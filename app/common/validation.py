from typing import Annotated

from fastapi.params import Path

SymbolParam = Annotated[
    str,
    Path(
        ...,
        description="Ticker symbol",
        example="AAPL",
        pattern=r"^[A-Za-z0-9\.\-]{1,10}$",
    ),
]
