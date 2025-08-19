from typing import Annotated

from fastapi.params import Path

from .constants import SYMBOL_REGEX

SymbolParam = Annotated[
    str,
    Path(
        ...,
        description="Ticker symbol (1-10 alphanumeric, may include . or -)",
        examples="AAPL",
        pattern=SYMBOL_REGEX,
        min_length=1,
        max_length=10,
        title="Symbol",
    ),
]
