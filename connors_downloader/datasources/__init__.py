"""
Data sources for fetching market data from various providers.

This module provides data source implementations following PEP 423 conventions
with a flat structure for better maintainability and imports.
"""

from connors_downloader.datasources.finnhub import FinnhubDataSource
from connors_downloader.datasources.fmp import FinancialModelingPrepDataSource
from connors_downloader.datasources.polygon import PolygonDataSource
from connors_downloader.datasources.yfinance import YfinanceDataSource

__all__ = [
    "YfinanceDataSource",
    "PolygonDataSource",
    "FinnhubDataSource",
    "FinancialModelingPrepDataSource",
]
