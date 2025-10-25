import os
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class DataFetchConfig:
    """Configuration for fetching data from a specific market"""

    name: str
    yf_ticker_suffix: str
    market: str


class DataFetchConfigManager:
    """Configuration management for data fetching"""

    def __init__(self) -> None:
        self.datafetch_configs = {
            "brazil": DataFetchConfig("brazil", ".SA", "brazil"),
            "australia": DataFetchConfig("australia", ".AX", "australia"),
            "america": DataFetchConfig("america", "", "america"),
            "canada": DataFetchConfig("canada", ".TO", "canada"),
            "uk": DataFetchConfig("uk", ".L", "uk"),
            "germany": DataFetchConfig("germany", ".DE", "germany"),
            "japan": DataFetchConfig("japan", ".T", "japan"),
            "hong_kong": DataFetchConfig("hong_kong", ".HK", "hong_kong"),
            "india": DataFetchConfig("india", ".NS", "india"),
            "crypto": DataFetchConfig("crypto", "", "crypto"),  # No suffix for crypto
        }

        self.default_config = os.getenv("DATAFETCH_CONFIG", "america")

    def get_market_config(self, config_name: str) -> DataFetchConfig:
        """Get datafetch configuration by name"""
        if config_name not in self.datafetch_configs:
            raise ValueError(
                f"Unknown datafetch config: {config_name}. Available: {list(self.datafetch_configs.keys())}"
            )
        return self.datafetch_configs[config_name]

    def list_configs(self) -> list[str]:
        """List all available datafetch configuration names"""
        return list(self.datafetch_configs.keys())

    def get_ticker_with_suffix(self, ticker: str, config_name: str) -> str:
        """Get ticker with appropriate suffix for the specified market"""
        config = self.get_market_config(config_name)
        if config.yf_ticker_suffix and not ticker.endswith(config.yf_ticker_suffix):
            return f"{ticker}{config.yf_ticker_suffix}"
        return ticker
