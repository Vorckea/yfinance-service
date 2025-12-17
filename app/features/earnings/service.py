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


def safe_float(x: Any) -> Optional[float]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    try:
        return float(x)
    except Exception:
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


def _extract_eps_and_revenue_from_row(series: pd.Series) -> tuple[Optional[float], Optional[float]]:
    """Robust EPS extractor handling multiple yfinance field conventions."""

    for col in ("Diluted EPS", "Basic EPS", "EPS", "Reported EPS", "EPS Actual"):
        if col in series.index and pd.notna(series.get(col)):
            try:
                return safe_float(series.get(col)), (
                    safe_float(
                        series.get(
                            series.index.intersection(
                                ["Total Revenue", "Revenue", "Operating Revenue"]
                            ).tolist()[0]
                        )
                    )
                    if any(
                        c in series.index for c in ["Total Revenue", "Revenue", "Operating Revenue"]
                    )
                    else None
                )
            except Exception:
                pass

    # compute EPS from Net Income and Shares
    income_cols = ["Net Income", "NetIncome", "Net Income Common Stockholders"]
    share_cols = [
        "Weighted Average Shs Out",
        "Weighted Average Shares",
        "Weighted Average Shs Out Dil",
        "Weighted Average Shares Dil",
        "Average Shares",
        "Shares Outstanding",
    ]
    net_income = None
    for f in income_cols:
        if f in series.index and pd.notna(series.get(f)):
            net_income = series.get(f)
            break

    if net_income is not None:
        for s in share_cols:
            if s in series.index:
                shares = series.get(s)

                if shares is None or pd.isna(shares) or shares == 0:
                    continue

                shares_f = float(shares)

                # Get revenue column
                revenue_col_candidates = ["Total Revenue", "Revenue", "Operating Revenue"]
                revenue_cols = series.index.intersection(revenue_col_candidates)

                revenue_f: float | None = None
                if len(revenue_cols) > 0:
                    revenue_val = series.get(revenue_cols[0])
                    if revenue_val is not None and pd.notna(revenue_val):
                        revenue_f = float(revenue_val)

                try:
                    return float(net_income) / shares_f, revenue_f
                except Exception:
                    continue

    # fallback revenue only
    for rev_col in ("Total Revenue", "Revenue", "Operating Revenue"):
        if rev_col in series.index and pd.notna(series.get(rev_col)):
            return None, safe_float(series.get(rev_col))

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
    df.index = pd.to_datetime(df.index, errors="coerce")

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
                if c in row.index and pd.notna(row.get(c)):
                    est = safe_float(row.get(c))
                    break
            for c in ("Surprise", "Surprise %"):
                if c in row.index and pd.notna(row.get(c)):
                    if c == "Surprise":
                        surprise = safe_float(row.get(c))
                    else:
                        surprise_pct = safe_float(row.get(c))

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
        info = await client.get_info(symbol)
        ts = info.get("nextEarningsDate") if isinstance(info, dict) else None

        if ts:
            try:
                next_earnings_date = safe_date(
                    datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                )

            except Exception:
                logger.warning(
                    "earnings.fetch.invalid_info_nextEarningsDate", extra={"symbol": symbol}
                )

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
