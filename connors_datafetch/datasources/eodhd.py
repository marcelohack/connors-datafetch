import os
from typing import Optional

import pandas as pd
import requests

from connors_datafetch.core.datasource import MarketDataSource
from connors_datafetch.core.registry import registry


@registry.register_datasource("eodhd")
class EodhdDataSource:
    """eodhd - EODHD (eodhd.com) data source implementation"""

    def __init__(self, api_key: Optional[str] = None):
        self.session = requests.Session()
        if api_key is None:
            api_key = os.getenv("EODHD_API_KEY")
            if not api_key:
                raise ValueError(
                    "EODHD API key is required. Please set the EODHD_API_KEY environment variable "
                    "or pass it as the api_key parameter."
                )
        self.api_key = api_key

    def fetch(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data from EODHD"""

        # EODHD symbols require an exchange code suffix (e.g. AAPL.US, BHP.AU);
        # default to the US virtual exchange when none is provided
        if "." not in symbol:
            symbol = f"{symbol}.US"

        # Daily/weekly/monthly use the EOD endpoint; sub-daily uses intraday
        eod_period_map = {
            "1d": "d",
            "1wk": "w",
            "1mo": "m",
        }
        intraday_interval_map = {
            "1m": "1m",
            "5m": "5m",
            "1h": "1h",
        }

        if interval in eod_period_map:
            url = f"https://eodhd.com/api/eod/{symbol}"
            params = {
                "from": pd.to_datetime(start).strftime("%Y-%m-%d"),
                "to": pd.to_datetime(end).strftime("%Y-%m-%d"),
                "period": eod_period_map[interval],
                "order": "a",
                "fmt": "json",
                "api_token": self.api_key,
            }
        elif interval in intraday_interval_map:
            # Intraday endpoint expects Unix timestamps (UTC)
            url = f"https://eodhd.com/api/intraday/{symbol}"
            params = {
                "from": str(int(pd.to_datetime(start).timestamp())),
                "to": str(int(pd.to_datetime(end).timestamp())),
                "interval": intraday_interval_map[interval],
                "fmt": "json",
                "api_token": self.api_key,
            }
        else:
            supported = ", ".join(
                sorted(list(eod_period_map) + list(intraday_interval_map))
            )
            raise ValueError(
                f"Interval '{interval}' not supported for EODHD datasource. "
                f"Supported intervals: {supported}"
            )

        response = self.session.get(url, params=params, timeout=20)
        if response.status_code != 200:
            raise RuntimeError(
                f"EODHD HTTP {response.status_code}: {response.text[:200]}"
            )
        results = response.json()

        if not isinstance(results, list) or not results:
            raise RuntimeError("EODHD returned no results")

        df = pd.DataFrame(results)[["open", "high", "low", "close", "volume"]]

        if interval in eod_period_map:
            # EOD rows carry a 'date' field (YYYY-MM-DD)
            df.index = pd.to_datetime([row["date"] for row in results])
        else:
            # Intraday rows carry a Unix 'timestamp' field (seconds, UTC)
            df.index = pd.to_datetime([row["timestamp"] for row in results], unit="s")
        df.index.name = "date"

        df = df.sort_index()

        return df
