"""
Connors DataFetch - Financial data fetcher with multiple data sources

This package provides tools for fetching financial market data from various sources
including stocks, forex, and cryptocurrency markets.
"""

__version__ = "0.1.0"

# Import registry to make it available at package level
from connors_datafetch.core.registry import registry

# Import services
from connors_datafetch.services.datafetch_service import DataFetchResult, DataFetchService

# Import config
from connors_datafetch.config.manager import DataFetchConfig, DataFetchConfigManager

__all__ = [
    "registry",
    "DataFetchService",
    "DataFetchResult",
    "DataFetchConfig",
    "DataFetchConfigManager",
]
