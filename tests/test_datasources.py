"""Tests for data source implementations"""

from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from connors_datafetch.datasources.finnhub import FinnhubDataSource
from connors_datafetch.datasources.fmp import FinancialModelingPrepDataSource
from connors_datafetch.datasources.polygon import PolygonDataSource
from connors_datafetch.datasources.yfinance import YfinanceDataSource


class TestYfinanceDataSource:
    """Test yfinance data source"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.yf_source = YfinanceDataSource()

    @patch("yfinance.download")
    def test_fetch_data_success(self, mock_download: Mock) -> None:
        """Test successful data fetch"""
        # Mock data
        mock_data = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [1000, 1100],
            }
        )
        mock_download.return_value = mock_data

        result = self.yf_source.fetch("AAPL", "2023-01-01", "2023-01-02")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        mock_download.assert_called_once_with(
            tickers="AAPL",
            start="2023-01-01",
            end="2023-01-02",
            interval="1d",
            progress=False,
            multi_level_index=False,
        )

    @patch("yfinance.download")
    def test_fetch_data_with_interval(self, mock_download: Mock) -> None:
        """Test data fetch with custom interval"""
        mock_data = pd.DataFrame({"Close": [100.0]})
        mock_download.return_value = mock_data

        self.yf_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1h")

        mock_download.assert_called_once_with(
            tickers="AAPL",
            start="2023-01-01",
            end="2023-01-02",
            interval="1h",
            progress=False,
            multi_level_index=False,
        )


class TestPolygonDataSource:
    """Test Polygon.io data source"""

    @patch("os.getenv")
    def test_init_with_env_api_key(self, mock_getenv: Mock) -> None:
        """Test initialization with environment variable API key"""
        mock_getenv.return_value = "env_api_key_123"
        polygon_source = PolygonDataSource()
        mock_getenv.assert_called_once_with("POLYGON_API_KEY")
        assert polygon_source.api_key == "env_api_key_123"

    def test_init_with_custom_api_key(self) -> None:
        """Test initialization with custom API key"""
        custom_key = "test_api_key_123"
        polygon_source = PolygonDataSource(api_key=custom_key)
        assert polygon_source.api_key == custom_key

    @patch("os.getenv")
    def test_init_without_api_key_raises_error(self, mock_getenv: Mock) -> None:
        """Test that initialization without API key raises ValueError"""
        mock_getenv.return_value = None

        with pytest.raises(ValueError, match="Polygon API key is required"):
            PolygonDataSource()

        mock_getenv.assert_called_once_with("POLYGON_API_KEY")

    @patch("requests.Session.get")
    def test_fetch_data_success(self, mock_get: Mock) -> None:
        """Test successful data fetch from Polygon"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resultsCount": 2,
            "results": [
                {
                    "t": 1640995200000,  # timestamp in ms
                    "o": 100.0,  # open
                    "h": 102.0,  # high
                    "l": 99.0,  # low
                    "c": 101.0,  # close
                    "v": 1000,  # volume
                },
                {
                    "t": 1641081600000,
                    "o": 101.0,
                    "h": 103.0,
                    "l": 100.0,
                    "c": 102.0,
                    "v": 1100,
                },
            ],
        }
        mock_get.return_value = mock_response

        polygon_source = PolygonDataSource(api_key="test_key")
        result = polygon_source.fetch("AAPL", "2023-01-01", "2023-01-02")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["open", "high", "low", "close", "volume"]
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "api.polygon.io/v2/aggs/ticker/AAPL/range/1/day" in call_args[0][0]
        assert call_args[1]["params"]["apiKey"] == "test_key"

    @patch("requests.Session.get")
    def test_fetch_data_empty_results(self, mock_get: Mock) -> None:
        """Test fetch when API returns no results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"resultsCount": 0}
        mock_get.return_value = mock_response

        polygon_source = PolygonDataSource(api_key="test_key")

        with pytest.raises(RuntimeError, match="polygon returned no results"):
            polygon_source.fetch("INVALID", "2023-01-01", "2023-01-02")

    @patch("requests.Session.get")
    def test_fetch_data_http_error(self, mock_get: Mock) -> None:
        """Test fetch when API returns HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        polygon_source = PolygonDataSource(api_key="invalid_key")

        with pytest.raises(RuntimeError, match="polygon HTTP 401"):
            polygon_source.fetch("AAPL", "2023-01-01", "2023-01-02")

    @patch("requests.Session.get")
    def test_fetch_data_with_intervals(self, mock_get: Mock) -> None:
        """Test data fetch with different intervals"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resultsCount": 1,
            "results": [
                {
                    "t": 1640995200000,
                    "o": 100.0,
                    "h": 102.0,
                    "l": 99.0,
                    "c": 101.0,
                    "v": 1000,
                }
            ],
        }
        mock_get.return_value = mock_response

        polygon_source = PolygonDataSource(api_key="test_key")

        # Test daily interval (default)
        result = polygon_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1d")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

        # Test weekly interval
        result = polygon_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1wk")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

        # Test monthly interval
        result = polygon_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1mo")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1


class TestFinnhubDataSource:
    """Test Finnhub data source"""

    @patch("os.getenv")
    def test_init_with_env_api_key(self, mock_getenv: Mock) -> None:
        """Test initialization with environment variable API key"""
        mock_getenv.return_value = "env_finnhub_key_123"
        finnhub_source = FinnhubDataSource()
        mock_getenv.assert_called_once_with("FINNHUB_API_KEY")
        assert finnhub_source.api_key == "env_finnhub_key_123"

    def test_init_with_custom_api_key(self) -> None:
        """Test initialization with custom API key"""
        custom_key = "test_finnhub_key_123"
        finnhub_source = FinnhubDataSource(api_key=custom_key)
        assert finnhub_source.api_key == custom_key

    @patch("os.getenv")
    def test_init_without_api_key_raises_error(self, mock_getenv: Mock) -> None:
        """Test that initialization without API key raises ValueError"""
        mock_getenv.return_value = None

        with pytest.raises(ValueError, match="Finnhub API key is required"):
            FinnhubDataSource()

        mock_getenv.assert_called_once_with("FINNHUB_API_KEY")

    @patch("requests.Session.get")
    def test_fetch_data_success(self, mock_get: Mock) -> None:
        """Test successful data fetch from Finnhub"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "s": "ok",
            "t": [1640995200, 1641081600],  # timestamps in seconds
            "o": [100.0, 101.0],  # open
            "h": [102.0, 103.0],  # high
            "l": [99.0, 100.0],  # low
            "c": [101.0, 102.0],  # close
            "v": [1000, 1100],  # volume
        }
        mock_get.return_value = mock_response

        finnhub_source = FinnhubDataSource(api_key="test_key")
        result = finnhub_source.fetch("AAPL", "2023-01-01", "2023-01-02")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["open", "high", "low", "close", "volume"]
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "finnhub.io/api/v1/stock/candle" in call_args[0][0]
        assert call_args[1]["params"]["token"] == "test_key"
        assert call_args[1]["params"]["symbol"] == "AAPL"

    @patch("requests.Session.get")
    def test_fetch_data_no_data(self, mock_get: Mock) -> None:
        """Test fetch when API returns no data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"s": "no_data"}
        mock_get.return_value = mock_response

        finnhub_source = FinnhubDataSource(api_key="test_key")

        with pytest.raises(RuntimeError, match="Finnhub returned no data"):
            finnhub_source.fetch("INVALID", "2023-01-01", "2023-01-02")

    @patch("requests.Session.get")
    def test_fetch_data_http_error(self, mock_get: Mock) -> None:
        """Test fetch when API returns HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        finnhub_source = FinnhubDataSource(api_key="invalid_key")

        with pytest.raises(RuntimeError, match="Finnhub HTTP 401"):
            finnhub_source.fetch("AAPL", "2023-01-01", "2023-01-02")

    @patch("requests.Session.get")
    def test_fetch_data_with_intervals(self, mock_get: Mock) -> None:
        """Test data fetch with different intervals"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "s": "ok",
            "t": [1640995200],
            "o": [100.0],
            "h": [102.0],
            "l": [99.0],
            "c": [101.0],
            "v": [1000],
        }
        mock_get.return_value = mock_response

        finnhub_source = FinnhubDataSource(api_key="test_key")

        # Test daily interval (default)
        result = finnhub_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1d")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

        # Test weekly interval
        result = finnhub_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1wk")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

        # Test monthly interval
        result = finnhub_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1mo")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1


class TestFMPDataSource:
    """Test FinancialModelingPrep data source"""

    @patch("os.getenv")
    def test_init_with_env_api_key(self, mock_getenv: Mock) -> None:
        """Test initialization with environment variable API key"""
        mock_getenv.return_value = "env_fmp_key_123"
        fmp_source = FinancialModelingPrepDataSource()
        mock_getenv.assert_called_once_with("FMP_API_KEY")
        assert fmp_source.api_key == "env_fmp_key_123"

    def test_init_with_custom_api_key(self) -> None:
        """Test initialization with custom API key"""
        custom_key = "test_fmp_key_123"
        fmp_source = FinancialModelingPrepDataSource(api_key=custom_key)
        assert fmp_source.api_key == custom_key

    @patch("os.getenv")
    def test_init_without_api_key_raises_error(self, mock_getenv: Mock) -> None:
        """Test that initialization without API key raises ValueError"""
        mock_getenv.return_value = None

        with pytest.raises(
            ValueError, match="FinancialModelingPrep API key is required"
        ):
            FinancialModelingPrepDataSource()

        mock_getenv.assert_called_once_with("FMP_API_KEY")

    @patch("requests.Session.get")
    def test_fetch_daily_data_success(self, mock_get: Mock) -> None:
        """Test successful daily data fetch from FMP"""
        # Mock HTTP response for daily data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "symbol": "AAPL",
            "historical": [
                {
                    "date": "2023-01-02",
                    "open": 101.0,
                    "high": 103.0,
                    "low": 100.0,
                    "close": 102.0,
                    "volume": 1100,
                },
                {
                    "date": "2023-01-01",
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "volume": 1000,
                },
            ],
        }
        mock_get.return_value = mock_response

        fmp_source = FinancialModelingPrepDataSource(api_key="test_key")
        result = fmp_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1d")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["open", "high", "low", "close", "volume"]
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert (
            "financialmodelingprep.com/api/v3/historical-price-full/AAPL"
            in call_args[0][0]
        )
        assert call_args[1]["params"]["apikey"] == "test_key"
        assert call_args[1]["params"]["from"] == "2023-01-01"
        assert call_args[1]["params"]["to"] == "2023-01-02"

    @patch("requests.Session.get")
    def test_fetch_weekly_data_success(self, mock_get: Mock) -> None:
        """Test successful weekly data fetch from FMP"""
        # Mock HTTP response for weekly data (direct array format)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2023-01-02",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "volume": 1000,
            }
        ]
        mock_get.return_value = mock_response

        fmp_source = FinancialModelingPrepDataSource(api_key="test_key")
        result = fmp_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1wk")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert list(result.columns) == ["open", "high", "low", "close", "volume"]

        # Verify correct endpoint for weekly data
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert (
            "financialmodelingprep.com/api/v3/historical-chart/1week/AAPL"
            in call_args[0][0]
        )

    @patch("requests.Session.get")
    def test_fetch_data_no_results(self, mock_get: Mock) -> None:
        """Test fetch when API returns no results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"symbol": "INVALID", "historical": []}
        mock_get.return_value = mock_response

        fmp_source = FinancialModelingPrepDataSource(api_key="test_key")

        with pytest.raises(RuntimeError, match="FMP returned no results"):
            fmp_source.fetch("INVALID", "2023-01-01", "2023-01-02")

    @patch("requests.Session.get")
    def test_fetch_data_http_error(self, mock_get: Mock) -> None:
        """Test fetch when API returns HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        fmp_source = FinancialModelingPrepDataSource(api_key="invalid_key")

        with pytest.raises(RuntimeError, match="FMP HTTP 401"):
            fmp_source.fetch("AAPL", "2023-01-01", "2023-01-02")

    @patch("requests.Session.get")
    def test_fetch_data_with_intervals(self, mock_get: Mock) -> None:
        """Test data fetch with different intervals"""
        mock_response = Mock()
        mock_response.status_code = 200

        fmp_source = FinancialModelingPrepDataSource(api_key="test_key")

        # Test daily interval
        mock_response.json.return_value = {
            "symbol": "AAPL",
            "historical": [
                {
                    "date": "2023-01-01",
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "volume": 1000,
                }
            ],
        }
        mock_get.return_value = mock_response
        result = fmp_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1d")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

        # Test weekly interval
        mock_response.json.return_value = [
            {
                "date": "2023-01-01",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "volume": 1000,
            }
        ]
        mock_get.return_value = mock_response
        result = fmp_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1wk")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

        # Test monthly interval
        result = fmp_source.fetch("AAPL", "2023-01-01", "2023-01-02", "1mo")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_fetch_data_unsupported_interval(self) -> None:
        """Test fetch with unsupported interval raises ValueError"""
        fmp_source = FinancialModelingPrepDataSource(api_key="test_key")

        with pytest.raises(ValueError, match="Unsupported interval: 5m"):
            fmp_source.fetch("AAPL", "2023-01-01", "2023-01-02", "5m")
