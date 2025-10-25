from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Dict, Protocol, Union

import pandas as pd


class MarketDataSource(Protocol):
    """Protocol for market data sources"""

    def fetch(
        self,
        symbol: str,
        start: Union[str, date, datetime],
        end: Union[str, date, datetime],
        interval: str = "1d",
    ) -> pd.DataFrame: ...

    # def validate_symbol(self, symbol: str) -> bool: ...
