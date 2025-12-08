"""Earnings service: fetches and normalizes earnings data."""

import asyncio
from datetime import date
from typing import Any, Optional

import pandas as pd

from ...clients.interface import YFinanceClientInterface
from ...utils.logger import logger
from .models import EarningRow, EarningsResponse


def _map_earnings(
    df: pd.DataFrame, symbol: str, frequency: str, next_earnings: Optional[date]
) -> EarningsResponse:
    """Map earnings DataFrame to EarningsResponse.

    Args:
        df: DataFrame with index as dates and columns like 'Reported EPS', 'Estimated EPS', 'Surprise', 'Surprise %'.
        symbol: The ticker symbol.
        frequency: 'quarterly' or 'annual'.
        next_earnings: Optional next earnings date from ticker.info.

    Returns:
        EarningsResponse with normalized rows.
    """
    rows = []

    for idx, row in df.iterrows():
        # Handle both DatetimeIndex and regular index
        if isinstance(idx, (pd.Timestamp, pd.DatetimeIndex)):
            row_date = idx.date() if hasattr(idx, "date") else idx
        else:
            row_date = idx

        # Extract values, handling NaN
        reported_eps = row.get("Reported EPS")
        estimated_eps = row.get("Estimated EPS")
        surprise = row.get("Surprise")
        surprise_pct = row.get("Surprise %")

        # Convert to Python types
        reported_eps = float(reported_eps) if pd.notna(reported_eps) else None
        estimated_eps = float(estimated_eps) if pd.notna(estimated_eps) else None
        surprise = float(surprise) if pd.notna(surprise) else None
        surprise_pct = float(surprise_pct) if pd.notna(surprise_pct) else None

        rows.append(
            EarningRow(
                earnings_date=row_date,
                reported_eps=reported_eps,
                estimated_eps=estimated_eps,
                surprise=surprise,
                surprise_percent=surprise_pct,
            )
        )

    # Sort by date descending (most recent first)
    rows.sort(key=lambda x: x.earnings_date, reverse=True)

    # Get last reported EPS (most recent with a reported value)
    last_eps = None
    for row in rows:
        if row.reported_eps is not None:
            last_eps = row.reported_eps
            break

    return EarningsResponse(
        symbol=symbol.upper(),
        frequency=frequency,
        rows=rows,
        next_earnings_date=next_earnings,
        last_eps=last_eps,
    )


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
    logger.info(
        "earnings.fetch.start", extra={"symbol": symbol, "frequency": frequency}
    )

    # Fetch earnings data
    earnings_df = await client.get_earnings(symbol, frequency)

    if earnings_df is None or earnings_df.empty:
        logger.warning(
            "earnings.fetch.no_data", extra={"symbol": symbol, "frequency": frequency}
        )
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"No {frequency} earnings data for {symbol}")

    # Try to get next earnings date from ticker info
    next_earnings = None
    try:
        info = await client.get_info(symbol)
        # yfinance provides 'nextEarningsDate' or 'earningsDate' in info
        if isinstance(info, dict):
            next_ts = info.get("nextEarningsDate")
            if next_ts:
                # Convert Unix timestamp to date if needed
                if isinstance(next_ts, (int, float)):
                    next_earnings = pd.Timestamp(next_ts, unit="s").date()
                elif isinstance(next_ts, (pd.Timestamp, date)):
                    next_earnings = (
                        next_ts.date() if isinstance(next_ts, pd.Timestamp) else next_ts
                    )
    except Exception as e:
        logger.warning(
            "earnings.fetch.next_date_error",
            extra={"symbol": symbol, "error": str(e)},
        )
        # Continue without next_earnings if lookup fails

    # Normalize to models asynchronously
    response = await asyncio.to_thread(_map_earnings, earnings_df, symbol, frequency, next_earnings)

    logger.info(
        "earnings.fetch.success",
        extra={"symbol": symbol, "frequency": frequency, "rows": len(response.rows)},
    )

    return response
