"""
Connors Downloader - Financial data downloader with multiple data sources

This package provides tools for downloading financial market data from various sources
including stocks, forex, and cryptocurrency markets.
"""

__version__ = "0.1.0"

# Import registry to make it available at package level
from connors_downloader.core.registry import registry

# Import services
from connors_downloader.services.download_service import DownloadResult, DownloadService

# Import config
from connors_downloader.config.manager import DownloadConfig, DownloadConfigManager

__all__ = [
    "registry",
    "DownloadService",
    "DownloadResult",
    "DownloadConfig",
    "DownloadConfigManager",
]
