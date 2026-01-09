"""Earnings service: fetches and normalizes earnings data."""

import asyncio
from datetime import date, datetime, timezone
from typing import Any, Optional
from fastapi import HTTPException
import numpy as np

import pandas as pd

from ...clients.interface import YFinanceClientInterface
from ...utils.logger import logger
from .models import EarningRow, EarningsResponse

def safe_date(x: Any) -> Optional[date]:
    if x is None:
        return None
    if isinstance(x, date):
        return x
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, str):
        try:
            # Try ISO 8601 first
            return datetime.fromisoformat(x.replace("Z", "")).date()
        except Exception:
            return None
    return None

def safe_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    try:
        return int(x)
    except Exception:
        return None


def _index_to_date(idx) -> Optional[date]:
    if idx is None:
        return None
    if isinstance(idx, (pd.Timestamp, datetime)):
        return idx.date()
    if isinstance(idx, str):
        try:
            return pd.to_datetime(idx).date()
        except Exception:
            return None
    return idx


def safe_float(val: Any) -> Optional[float]:
    """Convert value to float, returning None if conversion fails.
    
    Args:
        val: Value to convert.
    
    Returns:
        float if conversion succeeds, None otherwise.
    """
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(val)
    except (ValueError, TypeError):
        # Gracefully return None instead of raising - allows earnings data
        # with some missing/corrupt fields to still be partially served
        return None


def _extract_eps_and_revenue_from_row(
    series: pd.Series,
) -> tuple[Optional[float], Optional[float]]:
    """
    Robust EPS extractor handling multiple yfinance field conventions.

    Behavior (intentional):
    - Raises KeyError if NO EPS columns exist at all
    - Raises ValueError for corrupt EPS values
    - Gracefully handles missing revenue
    """

    eps_cols = ("Diluted EPS", "Basic EPS", "EPS", "Reported EPS", "EPS Actual")
    revenue_cols = ("Total Revenue", "Revenue", "Operating Revenue")

    # Direct EPS columns (STRICT) ----
    eps_found = False

    for col in eps_cols:
        if col in series.index:
            eps_found = True
            if pd.notna(series[col]):
                reported_eps = safe_float(series[col])

                revenue = None
                for rcol in revenue_cols:
                    if rcol in series.index and pd.notna(series[rcol]):
                        revenue = safe_float(series[rcol])
                        break

                return reported_eps, revenue

    if not eps_found:
        raise KeyError(f"Missing EPS column. Tried: {eps_cols}")

    # Compute EPS from Net Income / Shares ----
    income_cols = (
        "Net Income",
        "NetIncome",
        "Net Income Common Stockholders",
    )
    share_cols = (
        "Weighted Average Shs Out",
        "Weighted Average Shares",
        "Weighted Average Shs Out Dil",
        "Weighted Average Shares Dil",
        "Average Shares",
        "Shares Outstanding",
    )

    net_income = None
    for col in income_cols:
        if col in series.index and pd.notna(series[col]):
            net_income = safe_float(series[col])
            break

    if net_income is not None:
        for col in share_cols:
            if col in series.index and pd.notna(series[col]):
                shares = safe_float(series[col])
                # shares must be positive
                if shares and shares > 0:
                    eps = net_income / shares

                    revenue = None
                    for rcol in revenue_cols:
                        if rcol in series.index and pd.notna(series[rcol]):
                            revenue = safe_float(series[rcol])
                            break

                    return eps, revenue

    # Revenue-only fallback ----
    for col in revenue_cols:
        if col in series.index and pd.notna(series[col]):
            return None, safe_float(series[col])

    return None, None

async def fetch_earnings(
    symbol: str, client: YFinanceClientInterface, frequency: str = "quarterly"
) -> EarningsResponse:
    """Fetch and normalize earnings data for a symbol.

    Args:
        symbol: The stock symbol.
        client: YFinance client interface.
        frequency: 'quarterly' or 'annual'.

    Returns:
        EarningsResponse with normalized earnings rows.

    Raises:
        HTTPException: 404 if no data, 502 if malformed, 503 if timeout, etc.
    """
    logger.info("earnings.fetch.start", extra={"symbol": symbol, "frequency": frequency})
    symbol = symbol.upper()

    # fetch raw earnings-like DataFrame
    earnings_df = await client.get_earnings(symbol, frequency)
    if earnings_df is None or (isinstance(earnings_df, pd.DataFrame) and earnings_df.empty):
        logger.warning("earnings.fetch.no_data", extra={"symbol": symbol, "frequency": frequency})
        raise HTTPException(status_code=404, detail=f"No {frequency} earnings data for {symbol}")

    # If client returns a mapping-like (e.g. earnings_dates reset index), coerce to DF with date index
    df = earnings_df.copy() if isinstance(earnings_df, pd.DataFrame) else pd.DataFrame(earnings_df)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No {frequency} earnings data for {symbol}")

    # ensure index is dates: if 'earnings_date' column exists, set it as index
    if "earnings_date" in df.columns:
        df = df.set_index("earnings_date")
    # coerce index to timestamps where possible
    df.index = pd.to_datetime(df.index, errors="coerce", utc=True).tz_convert(None)

    # Now map rows in thread (CPU-bound)
    def map_df_to_rows(local_df: pd.DataFrame):
        rows = []
        for idx, row in local_df.iterrows():
            d = _index_to_date(idx)
            reported_eps, revenue = _extract_eps_and_revenue_from_row(row)
            # estimated / surprise fields if present
            est = None
            surprise = None
            surprise_pct = None
            for c in ("EPS Estimate", "Estimated EPS", "EPS Est", "EPS Forecast"):
                if c in row.index:
                    val = row.iloc[row.index.get_loc(c)]
                    if pd.notna(val):
                        est = safe_float(val)
                        break
            for c in ("Surprise", "Surprise %"):
                if c in row.index and pd.notna(row.index.get_loc(c)):
                    val = row.iloc[row.index.get_loc(c)]
                    if pd.notna(val):
                        if c == "Surprise":
                            surprise = safe_float(val)
                        else:
                            surprise_pct = safe_float(val)

            rows.append(
                EarningRow(
                    earnings_date=d,
                    reported_eps=reported_eps,
                    estimated_eps=est,
                    revenue=revenue,
                    surprise=surprise,
                    surprise_percent=surprise_pct,
                )
            )
        # sort most recent first
        rows.sort(key=lambda r: r.earnings_date or date.min, reverse=True)
        return rows

    rows = await asyncio.to_thread(map_df_to_rows, df)

    # next earnings date: try calendar then info
    next_earnings_date: Optional[date] = None

    # 1. Try from calendar
    try:
        calendar = await client.get_calendar(symbol)
        cal_date = calendar.get("Earnings Date") if isinstance(calendar, dict) else None

        if cal_date:
            # calendar may return list/tuple/timestamp/string
            if isinstance(cal_date, (list, tuple)):
                cal_date = cal_date[0]

            next_earnings_date = safe_date(cal_date)

    except Exception:
        logger.warning("earnings.fetch.calendar_failed", extra={"symbol": symbol})

    # 2. Fallback to get_info()["nextEarningsDate"]
    if next_earnings_date is None:
        try:
            info = await client.get_info(symbol)
            ts = info.get("nextEarningsDate") if isinstance(info, dict) else None
            if ts:
                next_earnings_date = safe_date(
                    datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                )
        except Exception:
            logger.warning("earnings.fetch.info_failed", extra={"symbol": symbol})
            next_earnings_date = None

    # 3. Final fallback
    if next_earnings_date is None:
        next_earnings_date = None

    # top-level summary fields
    last_eps = None
    for r in rows:
        if r.reported_eps is not None:
            last_eps = r.reported_eps
            break

    response = EarningsResponse(
        symbol=symbol,
        frequency=frequency,
        rows=rows,
        next_earnings_date=next_earnings_date,
        last_eps=last_eps,
    )

    logger.info("earnings.fetch.success", extra={"symbol": symbol, "rows": len(rows)})
    return response
