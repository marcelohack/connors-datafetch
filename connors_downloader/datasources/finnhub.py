import os
from typing import Optional

import pandas as pd
import requests

from connors_downloader.core.datasource import MarketDataSource
from connors_downloader.core.registry import registry


@registry.register_datasource("finnhub")
class FinnhubDataSource:
    """Finnhub datasource - Finnhub data source implementation"""

    def __init__(self, api_key: Optional[str] = None):
        self.session = requests.Session()
        if api_key is None:
            api_key = os.getenv("FINNHUB_API_KEY")
            if not api_key:
                raise ValueError(
                    "Finnhub API key is required. Please set the FINNHUB_API_KEY environment variable "
                    "or pass it as the api_key parameter."
                )
        self.api_key = api_key

    def fetch(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data from Finnhub"""

        # Finnhub uses different interval formats
        interval_map = {
            "1d": "D",
            "1wk": "W",
            "1mo": "M",
        }
        resolution = interval_map.get(interval, "D")

        # Convert dates to Unix timestamps
        start_ts = int(pd.to_datetime(start).timestamp())
        end_ts = int(pd.to_datetime(end).timestamp())

        url = "https://finnhub.io/api/v1/stock/candle"
        params = {
            "symbol": str(symbol),
            "resolution": str(resolution),
            "from": int(start_ts),
            "to": int(end_ts),
            "token": str(self.api_key),
        }

        response = self.session.get(url, params=params, timeout=20)
        if response.status_code != 200:
            raise RuntimeError(
                f"Finnhub HTTP {response.status_code}: {response.text[:200]}"
            )
        data = response.json()

        # Check if data contains an error
        if data.get("s") == "no_data":
            raise RuntimeError("Finnhub returned no data")

        # Finnhub returns arrays for each field
        if not data.get("c"):  # Check if close prices exist
            raise RuntimeError("Finnhub returned no results")

        df = pd.DataFrame(
            {
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
            }
        )

        # Convert timestamps to datetime index
        df.index = pd.to_datetime(data["t"], unit="s")

        # For daily data, normalize to date only (remove time component)
        if interval == "1d":
            df.index = df.index.normalize()

        df.index.name = "date"

        return df
