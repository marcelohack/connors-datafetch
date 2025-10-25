import os
from typing import Optional

import pandas as pd
import requests

from connors_downloader.core.datasource import MarketDataSource
from connors_downloader.core.registry import registry


@registry.register_datasource("polygon")
class PolygonDataSource:
    """polygon - Polygon.io data source implementation"""

    def __init__(self, api_key: Optional[str] = None):
        self.session = requests.Session()
        if api_key is None:
            api_key = os.getenv("POLYGON_API_KEY")
            if not api_key:
                raise ValueError(
                    "Polygon API key is required. Please set the POLYGON_API_KEY environment variable "
                    "or pass it as the api_key parameter."
                )
        self.api_key = api_key

    def fetch(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data from Polygon.io"""

        interval_map = {
            "1d": ("day", 1),
            "1wk": ("week", 1),
            "1mo": ("month", 1),
        }
        timespan, multiplier = interval_map.get(interval, ("day", 1))

        s = pd.to_datetime(start).strftime("%Y-%m-%d")
        e = pd.to_datetime(end).strftime("%Y-%m-%d")
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{s}/{e}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": "50000",
            "apiKey": self.api_key,
        }

        response = self.session.get(url, params=params, timeout=20)
        if response.status_code != 200:
            raise RuntimeError(
                f"polygon HTTP {response.status_code}: {response.text[:200]}"
            )
        data = response.json()

        results = data.get("results", [])
        if not results:
            raise RuntimeError("polygon returned no results")

        df = pd.DataFrame(results)[["o", "h", "l", "c", "v"]]
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index = pd.to_datetime([row["t"] for row in results], unit="ms")

        # For daily data, normalize to date only (remove time component)
        if interval == "1d":
            df.index = df.index.normalize()

        df.index.name = "date"

        return df
