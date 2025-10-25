"""
Test suite for DataFetchService

Tests the download service functionality including data validation,
market configurations, file operations, and error handling.
"""

import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from connors_datafetch.services.datafetch_service import DataFetchResult, DataFetchService


class TestDataFetchService:
    """Test suite for DataFetchService"""

    @pytest.fixture
    def service(self):
        """Create a DataFetchService instance for testing"""
        return DataFetchService()

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing"""
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        return pd.DataFrame(
            {
                "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
                "High": [105.0, 106.0, 107.0, 108.0, 109.0],
                "Low": [95.0, 96.0, 97.0, 98.0, 99.0],
                "Close": [104.0, 105.0, 106.0, 107.0, 108.0],
                "Volume": [1000000, 1100000, 1200000, 1300000, 1400000],
            },
            index=dates,
        )

    def test_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert service.registry is not None
        assert service.config_manager is not None
        assert hasattr(service, "logger")

    def test_get_datasources(self, service):
        """Test getting available datasources"""
        with patch.object(
            service.registry, "list_datasources", return_value=["yfinance", "polygon"]
        ):
            datasources = service.get_datasources()
            assert isinstance(datasources, list)
            assert "yfinance" in datasources
            assert "polygon" in datasources

    def test_get_datasources_error_handling(self, service):
        """Test datasources error handling"""
        with patch.object(
            service.registry,
            "list_datasources",
            side_effect=Exception("Registry error"),
        ):
            datasources = service.get_datasources()
            assert datasources == []

    def test_get_datasource_info(self, service):
        """Test getting datasource information"""
        with patch.object(
            service, "get_datasources", return_value=["yfinance", "polygon"]
        ):
            info = service.get_datasource_info()
            assert isinstance(info, dict)
            assert "yfinance" in info
            assert "polygon" in info
            assert info["yfinance"]["name"] == "yfinance"
            assert info["polygon"]["name"] == "polygon"
            assert info["polygon"]["requires_api_key"] is True

    def test_get_market_configs(self, service):
        """Test getting market configurations"""
        with patch.object(
            service.config_manager, "list_configs", return_value=["australia", "brazil"]
        ):
            configs = service.get_market_configs()
            assert isinstance(configs, list)
            assert "australia" in configs
            assert "brazil" in configs

    def test_get_market_config_info(self, service):
        """Test getting market configuration info"""
        mock_config = Mock()
        mock_config.name = "Australia"
        mock_config.yf_ticker_suffix = ".AX"
        mock_config.market = "australia"

        with patch.object(
            service.config_manager, "get_market_config", return_value=mock_config
        ):
            info = service.get_market_config_info("australia")
            assert info["name"] == "Australia"
            assert info["yf_ticker_suffix"] == ".AX"
            assert info["market"] == "australia"

    def test_get_market_config_info_error(self, service):
        """Test market config info error handling"""
        with patch.object(
            service.config_manager,
            "get_market_config",
            side_effect=Exception("Config error"),
        ):
            info = service.get_market_config_info("invalid")
            assert info == {}

    def test_get_supported_intervals(self, service):
        """Test getting supported intervals"""
        intervals = service.get_supported_intervals()
        assert isinstance(intervals, list)
        assert "1d" in intervals
        assert "1wk" in intervals
        assert "1mo" in intervals

    def test_get_default_dates(self, service):
        """Test getting default dates"""
        dates = service.get_default_dates()
        assert isinstance(dates, dict)
        assert "start" in dates
        assert "end" in dates

        # Check format
        start_date = datetime.strptime(dates["start"], "%Y-%m-%d").date()
        end_date = datetime.strptime(dates["end"], "%Y-%m-%d").date()
        assert start_date < end_date

    def test_get_available_timespans(self, service):
        """Test getting available timespans"""
        timeframes = service.get_available_timeframes()
        assert isinstance(timeframes, list)
        assert len(timeframes) > 0
        assert "1Y" in timeframes
        assert "6M" in timeframes
        assert "YTD" in timeframes

    def test_get_timespan_description(self, service):
        """Test getting timespan descriptions"""
        desc = service.get_timeframe_description("1Y")
        assert desc == "1 Year"

        desc = service.get_timeframe_description("YTD")
        assert desc == "Year to Date"

    def test_calculate_dates_from_timespan(self, service):
        """Test calculating dates from timespan"""
        # Test with timespan only
        dates = service.calculate_dates_from_timeframe(timeframe="1Y")
        assert isinstance(dates, dict)
        assert "start" in dates
        assert "end" in dates

        # Validate date format
        start_date = datetime.strptime(dates["start"], "%Y-%m-%d")
        end_date = datetime.strptime(dates["end"], "%Y-%m-%d")
        assert start_date < end_date

    def test_calculate_dates_from_timespan_with_custom_dates(self, service):
        """Test calculating dates with custom start/end override"""
        dates = service.calculate_dates_from_timeframe(
            timeframe="6M", start_date="2023-01-01", end_date="2023-12-31"
        )
        assert dates["start"] == "2023-01-01"
        assert dates["end"] == "2023-12-31"

    def test_calculate_dates_from_timespan_error_handling(self, service):
        """Test error handling in timespan calculation"""
        with patch(
            "connors_datafetch.core.timespan.TimespanCalculator.calculate_dates",
            side_effect=Exception("Timeframe error"),
        ):
            dates = service.calculate_dates_from_timeframe(timeframe="INVALID")
            # Should fallback to default dates
            assert isinstance(dates, dict)
            assert "start" in dates
            assert "end" in dates

    def test_validate_ticker_valid(self, service):
        """Test ticker validation with valid tickers"""
        test_cases = ["AAPL", "BHP.AX", "MSFT", "TSLA", "SPY"]

        for ticker in test_cases:
            result = service.validate_ticker(ticker)
            assert result["valid"] is True

    def test_validate_ticker_invalid(self, service):
        """Test ticker validation with invalid tickers"""
        test_cases = [
            ("", "Ticker cannot be empty"),
            ("AAPL@#$", "Ticker contains invalid characters"),
            ("VERYLONGTICKERSYMBOLS", "Ticker too long (max 20 characters)"),
        ]

        for ticker, expected_error in test_cases:
            result = service.validate_ticker(ticker)
            assert result["valid"] is False
            assert expected_error in result["error"]

    def test_preview_download_valid(self, service):
        """Test download preview with valid parameters"""
        mock_config = Mock()
        mock_config.name = "Australia"

        with (
            patch.object(
                service.config_manager, "get_market_config", return_value=mock_config
            ),
            patch.object(
                service.config_manager, "get_ticker_with_suffix", return_value="BHP.AX"
            ),
            patch.object(
                service, "_get_output_path", return_value=Path("/test/output.csv")
            ),
        ):

            preview = service.preview_download(
                datasource="yfinance",
                ticker="BHP",
                start="2024-01-01",
                end="2024-12-31",
                market="australia",
            )

            assert preview["valid"] is True
            assert preview["ticker"] == "BHP"
            assert preview["final_ticker"] == "BHP.AX"
            assert preview["datasource"] == "yfinance"
            assert preview["market_info"]["name"] == "Australia"

    def test_preview_download_invalid_ticker(self, service):
        """Test download preview with invalid ticker"""
        preview = service.preview_download(
            datasource="yfinance", ticker="", start="2024-01-01", end="2024-12-31"
        )

        assert preview["valid"] is False
        assert "Missing required parameters" in preview["error"]

    def test_preview_download_invalid_dates(self, service):
        """Test download preview with invalid date range"""
        preview = service.preview_download(
            datasource="yfinance", ticker="AAPL", start="2024-12-31", end="2024-01-01"
        )

        assert preview["valid"] is False
        assert "Start date must be before end date" in preview["error"]

    def test_preview_download_invalid_market(self, service):
        """Test download preview with invalid market"""
        with patch.object(
            service.config_manager,
            "get_market_config",
            side_effect=ValueError("Invalid market"),
        ):
            preview = service.preview_download(
                datasource="yfinance",
                ticker="BHP",
                start="2024-01-01",
                end="2024-12-31",
                market="invalid",
            )

            assert preview["valid"] is False
            assert "Invalid market: invalid" in preview["error"]

    @patch.dict(os.environ, {"CONNORS_HOME": ""}, clear=True)
    def test_download_data_success(self, service, sample_data):
        """Test successful data download"""
        mock_datasource = Mock()
        mock_datasource.fetch.return_value = sample_data

        with (
            patch.object(
                service.registry, "create_datasource", return_value=mock_datasource
            ),
            patch.object(
                service,
                "preview_download",
                return_value={
                    "valid": True,
                    "final_ticker": "AAPL",
                    "output_path": "/tmp/test.csv",
                },
            ),
            patch.object(service, "_ensure_directory_exists"),
            patch("pandas.DataFrame.to_csv") as mock_to_csv,
            patch.object(Path, "mkdir"),
        ):

            result = service.download_data(
                datasource="yfinance",
                ticker="AAPL",
                start="2024-01-01",
                end="2024-01-05",
            )

            assert isinstance(result, DataFetchResult)
            assert result.ticker == "AAPL"
            assert result.datasource == "yfinance"
            assert len(result.data) == 5
            mock_to_csv.assert_called_once()

    def test_download_data_no_data(self, service):
        """Test download when no data is found"""
        mock_datasource = Mock()
        mock_datasource.fetch.return_value = pd.DataFrame()  # Empty DataFrame

        with (
            patch.object(
                service.registry, "create_datasource", return_value=mock_datasource
            ),
            patch.object(
                service,
                "preview_download",
                return_value={
                    "valid": True,
                    "final_ticker": "INVALID",
                    "output_path": "/tmp/test.csv",
                },
            ),
        ):

            result = service.download_data(
                datasource="yfinance",
                ticker="INVALID",
                start="2024-01-01",
                end="2024-01-05",
            )

            # Should return a failed result
            assert result.success is False
            assert "No data found" in result.error

    def test_download_data_invalid_preview(self, service):
        """Test download with invalid preview"""
        with patch.object(
            service,
            "preview_download",
            return_value={"valid": False, "error": "Invalid ticker"},
        ):

            result = service.download_data(
                datasource="yfinance", ticker="", start="2024-01-01", end="2024-01-05"
            )

            # Should return a failed result
            assert result.success is False
            assert "Invalid ticker" in result.error

    def test_download_data_with_progress_callback(self, service, sample_data):
        """Test download with progress callback"""
        mock_datasource = Mock()
        mock_datasource.fetch.return_value = sample_data
        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)

        with (
            patch.object(
                service.registry, "create_datasource", return_value=mock_datasource
            ),
            patch.object(
                service,
                "preview_download",
                return_value={
                    "valid": True,
                    "final_ticker": "AAPL",
                    "output_path": "/tmp/test.csv",
                },
            ),
            patch.object(service, "_ensure_directory_exists"),
            patch("pandas.DataFrame.to_csv"),
            patch.object(Path, "mkdir"),
        ):

            service.download_data(
                datasource="yfinance",
                ticker="AAPL",
                start="2024-01-01",
                end="2024-01-05",
                progress_callback=progress_callback,
            )

            assert len(progress_messages) > 0
            assert "Validating parameters..." in progress_messages
            assert "Download completed!" in progress_messages

    def test_download_data_with_timespan(self, service, sample_data):
        """Test download data using timespan parameter"""
        mock_datasource = Mock()
        mock_datasource.fetch.return_value = sample_data

        with (
            patch.object(
                service.registry, "create_datasource", return_value=mock_datasource
            ),
            patch.object(
                service,
                "preview_download",
                return_value={
                    "valid": True,
                    "final_ticker": "AAPL",
                    "output_path": "/tmp/test.csv",
                },
            ),
            patch.object(service, "_ensure_directory_exists"),
            patch("pandas.DataFrame.to_csv") as mock_to_csv,
            patch.object(Path, "mkdir"),
            patch.object(
                service,
                "calculate_dates_from_timeframe",
                return_value={"start": "2023-06-15", "end": "2024-06-15"},
            ) as mock_calc_dates,
        ):

            result = service.download_data(
                datasource="yfinance",
                ticker="AAPL",
                timeframe="1Y",
            )

            # Verify timespan calculation was called
            mock_calc_dates.assert_called_once_with(
                timeframe="1Y", start_date=None, end_date=None
            )

            assert result.success is True
            assert result.ticker == "AAPL"
            assert result.datasource == "yfinance"
            assert result.start_date == "2023-06-15"
            assert result.end_date == "2024-06-15"

    def test_download_data_timespan_with_custom_dates(self, service, sample_data):
        """Test download data using timespan with custom date overrides"""
        mock_datasource = Mock()
        mock_datasource.fetch.return_value = sample_data

        with (
            patch.object(
                service.registry, "create_datasource", return_value=mock_datasource
            ),
            patch.object(
                service,
                "preview_download",
                return_value={
                    "valid": True,
                    "final_ticker": "AAPL",
                    "output_path": "/tmp/test.csv",
                },
            ),
            patch.object(service, "_ensure_directory_exists"),
            patch("pandas.DataFrame.to_csv"),
            patch.object(Path, "mkdir"),
            patch.object(
                service,
                "calculate_dates_from_timeframe",
                return_value={"start": "2023-01-01", "end": "2023-12-31"},
            ) as mock_calc_dates,
        ):

            result = service.download_data(
                datasource="yfinance",
                ticker="AAPL",
                start="2023-01-01",
                timeframe="6M",
            )

            # Verify timespan calculation was called with custom start
            mock_calc_dates.assert_called_once_with(
                timeframe="6M", start_date="2023-01-01", end_date=None
            )

            assert result.success is True

    def test_list_downloaded_files_empty(self, service):
        """Test listing files when directory doesn't exist"""
        with patch.object(service, "_get_app_home", return_value=Path("/nonexistent")):
            files = service.list_downloaded_files()
            assert files == []

    @patch.dict(os.environ, {"CONNORS_HOME": ""}, clear=True)
    def test_list_downloaded_files_with_files(self, service):
        """Test listing downloaded files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock files
            downloads_dir = Path(temp_dir) / "downloads" / "datasets"
            downloads_dir.mkdir(parents=True)

            # Create test files
            test_files = [
                "AAPL_yfinance_2024-01-01_2024-12-31_1d.csv",
                "BHP_australia_yfinance_2024-01-01_2024-12-31_1d.csv",
                "invalid_filename.csv",
            ]

            for filename in test_files:
                (downloads_dir / filename).touch()

            with patch.object(service, "_get_app_home", return_value=Path(temp_dir)):
                files = service.list_downloaded_files()

                assert len(files) == 2  # Only valid format files
                assert any(f["ticker"] == "AAPL" for f in files)
                assert any(
                    f["ticker"] == "BHP" and f["market"] == "australia" for f in files
                )

    def test_list_downloaded_files_with_filters(self, service):
        """Test listing downloaded files with filters"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloads_dir = Path(temp_dir) / "downloads" / "datasets"
            downloads_dir.mkdir(parents=True)

            # Create test files
            test_files = [
                "AAPL_yfinance_2024-01-01_2024-12-31_1d.csv",
                "MSFT_yfinance_2024-01-01_2024-12-31_1d.csv",
                "BHP_australia_yfinance_2024-01-01_2024-12-31_1d.csv",
            ]

            for filename in test_files:
                (downloads_dir / filename).touch()

            with patch.object(service, "_get_app_home", return_value=Path(temp_dir)):
                # Filter by ticker
                files = service.list_downloaded_files(ticker="AAPL")
                assert len(files) == 1
                assert files[0]["ticker"] == "AAPL"

                # Filter by datasource
                files = service.list_downloaded_files(datasource="yfinance")
                assert len(files) == 3

                # Filter by market
                files = service.list_downloaded_files(market="australia")
                assert len(files) == 1
                assert files[0]["ticker"] == "BHP"

    def test_delete_downloaded_file_success(self, service):
        """Test successful file deletion"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloads_dir = Path(temp_dir) / "downloads" / "datasets"
            downloads_dir.mkdir(parents=True)

            # Create test file
            test_file = downloads_dir / "AAPL_yfinance_2024-01-01_2024-12-31_1d.csv"
            test_file.touch()

            with patch.object(service, "_get_app_home", return_value=Path(temp_dir)):
                result = service.delete_downloaded_file(str(test_file))
                assert result is True
                assert not test_file.exists()

    def test_delete_downloaded_file_not_exists(self, service):
        """Test deleting non-existent file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloads_dir = Path(temp_dir) / "downloads" / "datasets"
            downloads_dir.mkdir(parents=True)

            test_file = downloads_dir / "nonexistent.csv"

            with patch.object(service, "_get_app_home", return_value=Path(temp_dir)):
                result = service.delete_downloaded_file(str(test_file))
                assert result is False

    def test_delete_downloaded_file_security_check(self, service):
        """Test file deletion security check"""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloads_dir = Path(temp_dir) / "downloads" / "datasets"
            downloads_dir.mkdir(parents=True)

            # Try to delete file outside downloads directory
            outside_file = Path(temp_dir) / "outside.csv"
            outside_file.touch()

            with patch.object(service, "_get_app_home", return_value=Path(temp_dir)):
                result = service.delete_downloaded_file(str(outside_file))
                assert result is False

    def test_get_output_path_no_market(self, service):
        """Test output path generation without market"""
        with (
            patch.object(service, "_get_app_home", return_value=Path("/home")),
            patch.object(service, "_ensure_directory_exists"),
        ):

            path = service._get_output_path(
                "AAPL", "yfinance", "2024-01-01", "2024-12-31", "1d"
            )
            expected = Path(
                "/home/downloads/datasets/AAPL_2024-01-01_2024-12-31_1d.csv"
            )
            assert path == expected

    def test_get_output_path_with_market(self, service):
        """Test output path generation with market"""
        with (
            patch.object(service, "_get_app_home", return_value=Path("/home")),
            patch.object(service, "_ensure_directory_exists"),
        ):

            path = service._get_output_path(
                "BHP", "yfinance", "2024-01-01", "2024-12-31", "1d", "australia"
            )
            expected = Path(
                "/home/downloads/datasets/BHP_australia_2024-01-01_2024-12-31_1d.csv"
            )
            assert path == expected

    def test_get_output_path_safe_ticker(self, service):
        """Test output path generation with unsafe characters in ticker"""
        with (
            patch.object(service, "_get_app_home", return_value=Path("/home")),
            patch.object(service, "_ensure_directory_exists"),
        ):

            path = service._get_output_path(
                "BRK/A", "yfinance", "2024-01-01", "2024-12-31", "1d"
            )
            expected = Path(
                "/home/downloads/datasets/BRK-A_2024-01-01_2024-12-31_1d.csv"
            )
            assert path == expected

    @patch.dict(os.environ, {"CONNORS_HOME": "/custom/home"})
    def test_get_app_home_with_env_var(self, service):
        """Test app home with CONNORS_HOME environment variable"""
        path = service._get_app_home()
        assert path == Path("/custom/home")

    @patch.dict(os.environ, {}, clear=True)
    def test_get_app_home_default(self, service):
        """Test app home without CONNORS_HOME environment variable"""
        path = service._get_app_home()
        assert path == Path.home() / ".connors"


if __name__ == "__main__":
    pytest.main([__file__])
