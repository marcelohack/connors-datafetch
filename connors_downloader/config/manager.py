import os
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class DownloadConfig:
    """Configuration for downloading data from a specific market"""

    name: str
    yf_ticker_suffix: str
    market: str


class DownloadConfigManager:
    """Configuration management for data downloading"""

    def __init__(self) -> None:
        self.download_configs = {
            "brazil": DownloadConfig("brazil", ".SA", "brazil"),
            "australia": DownloadConfig("australia", ".AX", "australia"),
            "america": DownloadConfig("america", "", "america"),
            "canada": DownloadConfig("canada", ".TO", "canada"),
            "uk": DownloadConfig("uk", ".L", "uk"),
            "germany": DownloadConfig("germany", ".DE", "germany"),
            "japan": DownloadConfig("japan", ".T", "japan"),
            "hong_kong": DownloadConfig("hong_kong", ".HK", "hong_kong"),
            "india": DownloadConfig("india", ".NS", "india"),
            "crypto": DownloadConfig("crypto", "", "crypto"),  # No suffix for crypto
        }

        self.default_config = os.getenv("DOWNLOAD_CONFIG", "america")

    def get_market_config(self, config_name: str) -> DownloadConfig:
        """Get download configuration by name"""
        if config_name not in self.download_configs:
            raise ValueError(
                f"Unknown download config: {config_name}. Available: {list(self.download_configs.keys())}"
            )
        return self.download_configs[config_name]

    def list_configs(self) -> list[str]:
        """List all available download configuration names"""
        return list(self.download_configs.keys())

    def get_ticker_with_suffix(self, ticker: str, config_name: str) -> str:
        """Get ticker with appropriate suffix for the specified market"""
        config = self.get_market_config(config_name)
        if config.yf_ticker_suffix and not ticker.endswith(config.yf_ticker_suffix):
            return f"{ticker}{config.yf_ticker_suffix}"
        return ticker
