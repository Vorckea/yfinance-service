"""Common constants for FastAPI endpoints."""

import re

# Symbol regex supports:
# - Standard US stocks (AAPL, GOOGL)
# - Crypto/currency pairs (BTC-USD, EURUSD)  
# - ISIN codes (IE00B4L5Y983)
# - Extended length symbols up to 20 chars
SYMBOL_REGEX = r"^[A-Za-z0-9\.\-=]{1,20}$"
SYMBOL_PATTERN = re.compile(SYMBOL_REGEX)
