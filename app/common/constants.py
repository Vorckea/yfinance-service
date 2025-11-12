"""Common constants for FastAPI endpoints."""

import re

SYMBOL_REGEX = r"^[A-Za-z0-9\.-]{1,10}$"
SYMBOL_PATTERN = re.compile(SYMBOL_REGEX)
