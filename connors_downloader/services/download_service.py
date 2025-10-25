"""
Download Service

Provides high-level interface for financial data downloading operations,
integrating with data sources and organized file storage.
"""

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

import connors_downloader.datasources.polygon

# Import all datasources to ensure registration
import connors_downloader.datasources.yfinance  # noqa: F401
import connors_downloader.datasources.ccxt  # noqa: F401
from connors_downloader.config.manager import DownloadConfigManager
from connors_downloader.core.registry import registry
from connors_downloader.core.timespan import TimespanCalculator
from connors_downloader.services.base import BaseService


@dataclass
class DownloadResult:
    """Container for download results"""

    ticker: str
    datasource: str
    market: Optional[str]
    data: Optional[pd.DataFrame]
    file_path: Optional[str]
    start_date: str
    end_date: str
    interval: str
    success: bool = True
    error: Optional[str] = None


class DownloadService(BaseService):
    """Service for financial data downloading operations"""

    def __init__(self) -> None:
        super().__init__()
        self.registry = registry
        self.config_manager = DownloadConfigManager()

    def get_datasources(self) -> List[str]:
        """Get list of available data sources"""
        try:
            return self.registry.list_datasources()
        except Exception as e:
            self.logger.error(f"Failed to get datasources: {e}")
            return []

    def get_datasource_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about each data source"""
        datasources_info = {
            "yfinance": {
                "name": "yfinance",
                "description": "Free financial data from Yahoo Finance",
                "requires_api_key": False,
                "supported_intervals": "1d, 1wk, 1mo",
                "global_coverage": True,
            },
            "polygon": {
                "name": "polygon",
                "description": "Professional financial data API",
                "requires_api_key": True,
                "supported_intervals": "1d, 1wk, 1mo",
                "global_coverage": True,
            },
            "finnhub": {
                "name": "finnhub",
                "description": "Finnhub Stock API for real-time market data",
                "requires_api_key": True,
                "supported_intervals": "1d, 1wk, 1mo",
                "global_coverage": True,
            },
            "fmp": {
                "name": "fmp",
                "description": "FinancialModelingPrep - Financial data API",
                "requires_api_key": True,
                "supported_intervals": "1d, 1wk, 1mo",
                "global_coverage": True,
            },
            "ccxt": {
                "name": "ccxt",
                "description": "Cryptocurrency data from 100+ exchanges via CCXT",
                "requires_api_key": False,
                "requires_exchange": True,
                "supported_intervals": "1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M",
                "global_coverage": True,
                "supported_exchanges": "binance, kraken, coinbase, and 100+ more",
            },
        }

        available_datasources = self.get_datasources()
        return {
            ds: info
            for ds, info in datasources_info.items()
            if ds in available_datasources
        }

    def get_market_configs(self) -> List[str]:
        """Get list of available market configurations"""
        try:
            return self.config_manager.list_configs()
        except Exception as e:
            self.logger.error(f"Failed to get market configs: {e}")
            return []

    def get_market_config_info(self, config_name: str) -> Dict[str, Any]:
        """Get detailed information about a market configuration"""
        try:
            self._validate_required_params(
                {"config_name": config_name}, ["config_name"]
            )

            config = self.config_manager.get_market_config(config_name)
            return {
                "name": config.name,
                "yf_ticker_suffix": config.yf_ticker_suffix,
                "market": config.market,
            }
        except Exception as e:
            self.logger.error(f"Failed to get market config info: {e}")
            return {}

    def get_supported_intervals(self) -> List[str]:
        """Get list of supported data intervals"""
        return ["1d", "1wk", "1mo"]

    def get_available_timeframes(self) -> List[str]:
        """Get list of available predefined timeframes"""
        return TimespanCalculator.get_available_timespans()

    def get_timeframe_description(self, timeframe: str) -> str:
        """Get human-readable description of timeframe"""
        return TimespanCalculator.get_timespan_description(timeframe)

    def get_default_dates(self) -> Dict[str, str]:
        """Get default start and end dates (1 year back from today)"""
        try:
            end = datetime.now().date()
            start = date(year=end.year - 1, month=end.month, day=end.day)

            return {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d"),
            }
        except Exception as e:
            self.logger.error(f"Failed to calculate default dates: {e}")
            # Fallback
            return {"start": "2024-01-01", "end": "2024-12-31"}

    def calculate_dates_from_timeframe(
        self,
        timeframe: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Calculate start and end dates based on timeframe or explicit dates.

        Args:
            timeframe: Pre-defined timeframe (e.g., "1Y", "6M", "YTD") or None for custom dates
            start_date: Custom start date in YYYY-MM-DD format
            end_date: Custom end date in YYYY-MM-DD format

        Returns:
            Dictionary with 'start' and 'end' keys containing dates in YYYY-MM-DD format
        """
        try:
            start, end = TimespanCalculator.calculate_dates(
                timespan=timeframe, start_date=start_date, end_date=end_date
            )
            return {"start": start, "end": end}
        except Exception as e:
            self.logger.error(f"Failed to calculate dates from timeframe: {e}")
            # Fallback to default 1Y
            return self.get_default_dates()

    def validate_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Validate ticker symbol format

        Accepts:
        - Stock tickers: AAPL, MSFT.AX, BHP-AU (alphanumeric with . and -)
        - Crypto pairs: BTC/USDT, ETH/USD (alphanumeric with /)

        Returns dict with validation results
        """
        if not ticker:
            return {"valid": False, "error": "Ticker cannot be empty"}

        # Allow alphanumeric plus common separators: . - /
        # Remove these characters and check if remaining is alphanumeric
        if not ticker.replace(".", "").replace("-", "").replace("/", "").isalnum():
            return {"valid": False, "error": "Ticker contains invalid characters"}

        # Relax length check for crypto pairs (e.g., BTC/USDT is 8 chars)
        if len(ticker) > 20:
            return {"valid": False, "error": "Ticker too long (max 20 characters)"}

        return {"valid": True}

    def preview_download(
        self,
        datasource: str,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
        market: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Preview download parameters without actually downloading

        Args:
            datasource: Data source name
            ticker: Stock ticker symbol
            start: Start date (YYYY-MM-DD) - optional if timeframe provided
            end: End date (YYYY-MM-DD) - optional if timeframe provided
            interval: Data interval (1d, 1wk, 1mo)
            market: Optional market configuration
            timeframe: Pre-defined timeframe (e.g., "1Y", "6M", "YTD")

        Returns:
            Information about what would be downloaded
        """
        try:
            # Calculate dates from timeframe if not provided
            if timeframe or not (start and end):
                date_result = self.calculate_dates_from_timeframe(
                    timeframe=timeframe, start_date=start, end_date=end
                )
                start = date_result["start"]
                end = date_result["end"]

            self._validate_required_params(
                {
                    "datasource": datasource,
                    "ticker": ticker,
                    "start": start,
                    "end": end,
                },
                ["datasource", "ticker", "start", "end"],
            )

            # Validate ticker
            ticker_validation = self.validate_ticker(ticker)
            if not ticker_validation["valid"]:
                return {"valid": False, "error": ticker_validation["error"]}

            # Get final ticker with market suffix if applicable
            final_ticker = ticker
            market_info = None
            if market:
                try:
                    market_config = self.config_manager.get_market_config(market)
                    final_ticker = self.config_manager.get_ticker_with_suffix(
                        ticker, market
                    )
                    market_info = {
                        "name": market_config.name,
                        "ticker_with_suffix": final_ticker,
                    }
                except ValueError:
                    return {"valid": False, "error": f"Invalid market: {market}"}

            # Generate output path
            output_path = self._get_output_path(
                ticker, datasource, start, end, interval, market, exchange=None, include_datasource=False, timeframe=timeframe
            )

            # Validate date range
            try:
                start_date = pd.to_datetime(start).date()
                end_date = pd.to_datetime(end).date()
                if start_date >= end_date:
                    return {
                        "valid": False,
                        "error": "Start date must be before end date",
                    }
            except ValueError:
                return {"valid": False, "error": "Invalid date format (use YYYY-MM-DD)"}

            return {
                "valid": True,
                "ticker": ticker,
                "final_ticker": final_ticker,
                "datasource": datasource,
                "start": start,
                "end": end,
                "interval": interval,
                "market_info": market_info,
                "output_path": str(output_path),
                "filename": output_path.name,
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    def download_data(
        self,
        datasource: str,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
        market: Optional[str] = None,
        output_file: Optional[str] = None,
        output_format: str = "csv",
        progress_callback: Optional[Callable[[str], None]] = None,
        timeframe: Optional[str] = None,
        exchange: Optional[str] = None,
        include_datasource: bool = False,
    ) -> DownloadResult:
        """
        Download financial data and save to specified format

        Args:
            datasource: Data source name
            ticker: Stock ticker symbol
            start: Start date (YYYY-MM-DD) - optional if timeframe provided
            end: End date (YYYY-MM-DD) - optional if timeframe provided
            interval: Data interval (1d, 1wk, 1mo for stocks; 1m-1M for crypto)
            market: Optional market configuration
            output_file: Optional custom output file path
            output_format: Output format ('csv' or 'json')
            progress_callback: Optional callback for progress updates
            timeframe: Pre-defined timeframe (e.g., "1Y", "6M", "YTD")
            exchange: Exchange name for ccxt datasource (e.g., "binance", "kraken")

        Returns:
            DownloadResult object containing data and metadata
        """
        try:
            # Calculate dates from timeframe if not provided
            if timeframe or not (start and end):
                date_result = self.calculate_dates_from_timeframe(
                    timeframe=timeframe, start_date=start, end_date=end
                )
                start = date_result["start"]
                end = date_result["end"]
            # Validate output format
            if output_format.lower() not in ["csv", "json"]:
                raise ValueError(
                    f"Unsupported output format: {output_format}. Supported formats: csv, json"
                )

            if progress_callback:
                progress_callback("Validating parameters...")

            # Preview/validate the download
            preview = self.preview_download(
                datasource, ticker, start, end, interval, market
            )
            if not preview["valid"]:
                raise ValueError(preview["error"])

            if progress_callback:
                progress_callback("Creating data source...")

            # Create datasource instance with exchange parameter if provided
            kwargs = {}
            if exchange:
                kwargs['exchange'] = exchange

            datasource_instance = self.registry.create_datasource(datasource, **kwargs)

            if progress_callback:
                progress_callback(f"Fetching data for {preview['final_ticker']}...")

            # Fetch data
            df = datasource_instance.fetch(
                symbol=preview["final_ticker"], start=start, end=end, interval=interval
            )

            if df.empty:
                raise ValueError(
                    f"No data found for {preview['final_ticker']} in the specified date range"
                )

            if progress_callback:
                progress_callback(f"Retrieved {len(df)} data points...")

            # Determine output path
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = self._get_output_path_with_format(
                    ticker, datasource, start, end, interval, market, output_format, exchange, include_datasource, timeframe
                )
                self._ensure_directory_exists(output_path.parent)

            format_upper = output_format.upper()
            if progress_callback:
                progress_callback(f"Saving to {format_upper}...")

            # Save data in the specified format with lowercase column names
            # Convert columns to lowercase for export
            df_export = df.copy()
            df_export.columns = df_export.columns.str.lower()
            df_export.index.name = (
                df_export.index.name.lower() if df_export.index.name else "date"
            )

            if output_format.lower() == "csv":
                # For CSV export, ensure dates are formatted as date strings for daily data
                if interval == "1d" and isinstance(df_export.index, pd.DatetimeIndex):
                    df_export_csv = df_export.copy()
                    df_export_csv.index = df_export_csv.index.strftime("%Y-%m-%d")
                    df_export_csv.to_csv(output_path)
                else:
                    df_export.to_csv(output_path)
            elif output_format.lower() == "json":
                # Convert to JSON format with proper handling of date and numeric types
                # Reset index to include it in the JSON output
                df_export_reset = df_export.reset_index()

                # Custom date serializer to format dates properly
                def date_serializer(obj):
                    if isinstance(obj, pd.Timestamp):
                        # For daily data, return just the date part
                        if interval == "1d":
                            return obj.strftime("%Y-%m-%d")
                        else:
                            # For weekly/monthly, include time if needed
                            return obj.strftime("%Y-%m-%d")
                    return str(obj)

                # Convert to JSON with proper date handling - direct array format
                json_records = df_export_reset.to_dict("records")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(json_records, f, indent=2, default=date_serializer)

            if progress_callback:
                progress_callback("Download completed!")

            return DownloadResult(
                ticker=ticker,
                datasource=datasource,
                market=market,
                data=df,
                file_path=str(output_path),
                start_date=start,
                end_date=end,
                interval=interval,
            )

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            if progress_callback:
                progress_callback(f"Error: {e}")
            return DownloadResult(
                ticker=ticker,
                datasource=datasource,
                market=market,
                data=None,
                file_path=None,
                start_date=start,
                end_date=end,
                interval=interval,
                success=False,
                error=f"Download failed: {e}",
            )

    def list_downloaded_files(
        self,
        ticker: Optional[str] = None,
        datasource: Optional[str] = None,
        market: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List previously downloaded files with optional filtering

        Returns list of file information dictionaries
        """
        try:
            downloads_dir = self._get_app_home() / "downloads" / "datasets"

            if not downloads_dir.exists():
                return []

            files_info = []
            for file_path in downloads_dir.glob("*.csv"):
                try:
                    # Parse filename: {ticker}_{market}_{datasource}_{start}_{end}_{interval}.csv
                    name_parts = file_path.stem.split("_")

                    if (
                        len(name_parts) < 5
                    ):  # At least ticker_datasource_start_end_interval
                        continue

                    # Handle case with and without market
                    if len(name_parts) >= 6:  # Has market
                        file_ticker, file_market, file_datasource = name_parts[:3]
                        file_start, file_end, file_interval = name_parts[-3:]
                    else:  # No market
                        file_ticker, file_datasource = name_parts[:2]
                        file_start, file_end, file_interval = name_parts[-3:]
                        file_market = None

                    # Apply filters
                    if ticker and file_ticker != ticker:
                        continue
                    if datasource and file_datasource != datasource:
                        continue
                    if market and file_market != market:
                        continue

                    # Get file stats
                    stats = file_path.stat()

                    files_info.append(
                        {
                            "filename": file_path.name,
                            "path": str(file_path),
                            "ticker": file_ticker,
                            "market": file_market,
                            "datasource": file_datasource,
                            "start_date": file_start,
                            "end_date": file_end,
                            "interval": file_interval,
                            "size_bytes": stats.st_size,
                            "modified": datetime.fromtimestamp(stats.st_mtime),
                        }
                    )

                except Exception:
                    # Skip files that don't match expected format
                    continue

            # Sort by modification time (newest first)
            files_info.sort(
                key=lambda x: (
                    x["modified"]
                    if isinstance(x["modified"], datetime)
                    else datetime.min
                ),
                reverse=True,
            )
            return files_info

        except Exception as e:
            self.logger.error(f"Failed to list downloaded files: {e}")
            return []

    def delete_downloaded_file(self, file_path: str) -> bool:
        """
        Delete a downloaded file

        Returns True if successful, False otherwise
        """
        try:
            file_path_obj = Path(file_path)

            # Security check - ensure file is in the downloads directory
            downloads_dir = self._get_app_home() / "downloads" / "datasets"
            if not file_path_obj.is_relative_to(downloads_dir):
                raise ValueError("File is not in the downloads directory")

            if file_path_obj.exists():
                file_path_obj.unlink()
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    def _timeframe_to_filename(self, timeframe: str) -> str:
        """Convert timeframe code to filename-friendly format"""
        timeframe_map = {
            "1D": "1day",
            "2D": "2days",
            "3D": "3days",
            "5D": "5days",
            "1W": "1week",
            "2W": "2weeks",
            "3W": "3weeks",
            "1M": "1month",
            "2M": "2months",
            "3M": "3months",
            "6M": "6months",
            "1Y": "1year",
            "2Y": "2years",
            "3Y": "3years",
            "5Y": "5years",
            "YTD": "ytd",
            "MAX": "max",
        }
        return timeframe_map.get(timeframe, timeframe.lower())

    def _get_output_path(
        self,
        ticker: str,
        datasource: str,
        start: str,
        end: str,
        interval: str,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        include_datasource: bool = False,
        timeframe: Optional[str] = None,
    ) -> Path:
        """Generate output path within app folder downloads/datasets directory (CSV format)"""
        return self._get_output_path_with_format(
            ticker, datasource, start, end, interval, market, "csv", exchange, include_datasource, timeframe
        )

    def _get_output_path_with_format(
        self,
        ticker: str,
        datasource: str,
        start: str,
        end: str,
        interval: str,
        market: Optional[str] = None,
        output_format: str = "csv",
        exchange: Optional[str] = None,
        include_datasource: bool = False,
        timeframe: Optional[str] = None,
    ) -> Path:
        """Generate output path within app folder downloads/datasets directory with specified format"""
        app_home = self._get_app_home()
        datasets_dir = app_home / "downloads" / "datasets"
        self._ensure_directory_exists(datasets_dir)

        # Clean ticker symbol (remove any path-unsafe characters)
        safe_ticker = ticker.replace("/", "-").replace("\\", "-").replace(":", "-")

        # Get file extension based on format
        extension = output_format.lower()

        # Determine period string: use timeframe if provided, otherwise use start_end dates
        if timeframe:
            period_str = self._timeframe_to_filename(timeframe)
        else:
            period_str = f"{start}_{end}"

        # Generate filename based on datasource type
        # Default patterns (include_datasource=False):
        #   With timeframe: <ticker>_[<exchange>|<market>]_<timeframe>_<interval>.<ext>
        #   With dates: <ticker>_[<exchange>|<market>]_<start>_<end>_<interval>.<ext>
        #
        # With include_datasource=True:
        #   With timeframe: <ticker>_[<exchange>|<market>]_<datasource>_<timeframe>_<interval>.<ext>
        #   With dates: <ticker>_[<exchange>|<market>]_<datasource>_<start>_<end>_<interval>.<ext>

        if datasource == "ccxt" and exchange:
            # Crypto format
            if include_datasource:
                filename = f"{safe_ticker}_{exchange}_{datasource}_{period_str}_{interval}.{extension}"
            else:
                filename = f"{safe_ticker}_{exchange}_{period_str}_{interval}.{extension}"
        elif market and market != "america":
            # Stock with non-default market
            if include_datasource:
                filename = f"{safe_ticker}_{market}_{datasource}_{period_str}_{interval}.{extension}"
            else:
                filename = f"{safe_ticker}_{market}_{period_str}_{interval}.{extension}"
        else:
            # Stock with default market or no market
            if include_datasource:
                filename = f"{safe_ticker}_{datasource}_{period_str}_{interval}.{extension}"
            else:
                filename = f"{safe_ticker}_{period_str}_{interval}.{extension}"

        return datasets_dir / filename

    def _get_app_home(self) -> Path:
        """Get the application home directory"""
        connors_home = os.environ.get("CONNORS_HOME")
        if connors_home:
            return Path(connors_home)
        else:
            return Path.home() / ".connors"
