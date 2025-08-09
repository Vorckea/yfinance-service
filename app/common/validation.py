from typing import Annotated

from fastapi.params import Path

from .constants import SYMBOL_REGEX

SymbolParam = Annotated[
    str,
    Path(
        ...,
        description="Ticker symbol",
        example="AAPL",
        pattern=SYMBOL_REGEX,
    ),
]
