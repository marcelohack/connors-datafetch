"""Tests for data source implementations"""

from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from connors_datafetch.datasources.eodhd import EodhdDataSource
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
            prepost=False,
            progress=False,
            multi_level_index=False,
        )

    @patch("yfinance.download")
    def test_fetch_data_with_interval(self, mock_download: Mock) -> None:
        """Test data fetch with custom intraday interval"""
        mock_data = pd.DataFrame({"Close": [100.0]})
        mock_download.return_value = mock_data

        self.yf_source.fetch("AAPL", "2024-01-01", "2024-01-02", "1h")

        mock_download.assert_called_once_with(
            tickers="AAPL",
            start="2024-01-01",
            end="2024-01-02",
            interval="1h",
            prepost=False,
            progress=False,
            multi_level_index=False,
        )

    @patch("yfinance.download")
    def test_fetch_data_with_extended_hours(self, mock_download: Mock) -> None:
        """Test data fetch with extended hours enabled"""
        mock_data = pd.DataFrame({"Close": [100.0]})
        mock_download.return_value = mock_data

        self.yf_source.fetch(
            "AAPL", "2024-01-01", "2024-01-02", "5m", extended_hours=True
        )

        mock_download.assert_called_once_with(
            tickers="AAPL",
            start="2024-01-01",
            end="2024-01-02",
            interval="5m",
            prepost=True,
            progress=False,
            multi_level_index=False,
        )

    def test_fetch_unsupported_interval(self) -> None:
        """Test that unsupported interval raises ValueError"""
        with pytest.raises(ValueError, match="not supported for yfinance"):
            self.yf_source.fetch("AAPL", "2024-01-01", "2024-01-02", "3m")

    def test_fetch_1m_exceeds_lookback(self) -> None:
        """Test that 1m interval with >7 day range raises ValueError"""
        with pytest.raises(ValueError, match="maximum lookback of 7 days"):
            self.yf_source.fetch("AAPL", "2024-01-01", "2024-01-15", "1m")

    def test_fetch_5m_exceeds_lookback(self) -> None:
        """Test that 5m interval with >60 day range raises ValueError"""
        with pytest.raises(ValueError, match="maximum lookback of 60 days"):
            self.yf_source.fetch("AAPL", "2024-01-01", "2024-06-01", "5m")

    @patch("yfinance.download")
    def test_fetch_1m_within_lookback(self, mock_download: Mock) -> None:
        """Test that 1m interval within 7 day range succeeds"""
        mock_data = pd.DataFrame({"Close": [100.0]})
        mock_download.return_value = mock_data

        self.yf_source.fetch("AAPL", "2024-01-01", "2024-01-05", "1m")
        mock_download.assert_called_once()


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

    @patch("requests.Session.get")
    def test_fetch_intraday_intervals(self, mock_get: Mock) -> None:
        """Test data fetch with intraday intervals"""
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

        # Test 5m interval
        result = polygon_source.fetch("AAPL", "2024-01-01", "2024-01-02", "5m")
        assert isinstance(result, pd.DataFrame)
        call_args = mock_get.call_args
        assert "/range/5/minute/" in call_args[0][0]

        # Test 1h interval
        result = polygon_source.fetch("AAPL", "2024-01-01", "2024-01-02", "1h")
        call_args = mock_get.call_args
        assert "/range/1/hour/" in call_args[0][0]

    def test_fetch_unsupported_interval(self) -> None:
        """Test that unsupported interval raises ValueError"""
        polygon_source = PolygonDataSource(api_key="test_key")
        with pytest.raises(ValueError, match="not supported for Polygon"):
            polygon_source.fetch("AAPL", "2024-01-01", "2024-01-02", "3m")


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

    @patch("requests.Session.get")
    def test_fetch_intraday_intervals(self, mock_get: Mock) -> None:
        """Test data fetch with intraday intervals"""
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

        # Test 5m interval maps to resolution "5"
        finnhub_source.fetch("AAPL", "2024-01-01", "2024-01-02", "5m")
        call_args = mock_get.call_args
        assert call_args[1]["params"]["resolution"] == "5"

        # Test 1h interval maps to resolution "60"
        finnhub_source.fetch("AAPL", "2024-01-01", "2024-01-02", "1h")
        call_args = mock_get.call_args
        assert call_args[1]["params"]["resolution"] == "60"

    def test_fetch_unsupported_interval(self) -> None:
        """Test that unsupported interval raises ValueError"""
        finnhub_source = FinnhubDataSource(api_key="test_key")
        with pytest.raises(ValueError, match="not supported for Finnhub"):
            finnhub_source.fetch("AAPL", "2024-01-01", "2024-01-02", "3m")


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

        with pytest.raises(ValueError, match="not supported for FMP"):
            fmp_source.fetch("AAPL", "2023-01-01", "2023-01-02", "3m")

    @patch("requests.Session.get")
    def test_fetch_intraday_data(self, mock_get: Mock) -> None:
        """Test fetch with intraday intervals uses historical-chart endpoint"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2024-01-02 09:30:00",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "volume": 1000,
            }
        ]
        mock_get.return_value = mock_response

        fmp_source = FinancialModelingPrepDataSource(api_key="test_key")
        result = fmp_source.fetch("AAPL", "2024-01-01", "2024-01-02", "5m")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

        # Verify correct endpoint for intraday data
        call_args = mock_get.call_args
        assert "historical-chart/5min/AAPL" in call_args[0][0]


class TestEodhdDataSource:
    """Test EODHD data source"""

    @patch("os.getenv")
    def test_init_with_env_api_key(self, mock_getenv: Mock) -> None:
        """Test initialization with environment variable API key"""
        mock_getenv.return_value = "env_eodhd_key_123"
        eodhd_source = EodhdDataSource()
        mock_getenv.assert_called_once_with("EODHD_API_KEY")
        assert eodhd_source.api_key == "env_eodhd_key_123"

    def test_init_with_custom_api_key(self) -> None:
        """Test initialization with custom API key"""
        custom_key = "test_eodhd_key_123"
        eodhd_source = EodhdDataSource(api_key=custom_key)
        assert eodhd_source.api_key == custom_key

    @patch("os.getenv")
    def test_init_without_api_key_raises_error(self, mock_getenv: Mock) -> None:
        """Test that initialization without API key raises ValueError"""
        mock_getenv.return_value = None

        with pytest.raises(ValueError, match="EODHD API key is required"):
            EodhdDataSource()

        mock_getenv.assert_called_once_with("EODHD_API_KEY")

    @patch("requests.Session.get")
    def test_fetch_daily_data_success(self, mock_get: Mock) -> None:
        """Test successful daily data fetch from EODHD"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2023-01-01",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "adjusted_close": 100.5,
                "volume": 1000,
            },
            {
                "date": "2023-01-02",
                "open": 101.0,
                "high": 103.0,
                "low": 100.0,
                "close": 102.0,
                "adjusted_close": 101.5,
                "volume": 1100,
            },
        ]
        mock_get.return_value = mock_response

        eodhd_source = EodhdDataSource(api_key="test_key")
        result = eodhd_source.fetch("AAPL.US", "2023-01-01", "2023-01-02")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["open", "high", "low", "close", "volume"]
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "eodhd.com/api/eod/AAPL.US" in call_args[0][0]
        assert call_args[1]["params"]["api_token"] == "test_key"
        assert call_args[1]["params"]["from"] == "2023-01-01"
        assert call_args[1]["params"]["to"] == "2023-01-02"
        assert call_args[1]["params"]["period"] == "d"
        assert call_args[1]["params"]["fmt"] == "json"

    @patch("requests.Session.get")
    def test_fetch_appends_us_exchange_suffix(self, mock_get: Mock) -> None:
        """Test that symbols without an exchange suffix default to .US"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2023-01-01",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "adjusted_close": 100.5,
                "volume": 1000,
            }
        ]
        mock_get.return_value = mock_response

        eodhd_source = EodhdDataSource(api_key="test_key")
        eodhd_source.fetch("AAPL", "2023-01-01", "2023-01-02")

        call_args = mock_get.call_args
        assert "eodhd.com/api/eod/AAPL.US" in call_args[0][0]

    @patch("requests.Session.get")
    def test_fetch_intraday_data(self, mock_get: Mock) -> None:
        """Test fetch with intraday intervals uses intraday endpoint"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "timestamp": 1704189000,
                "gmtoffset": 0,
                "datetime": "2024-01-02 09:30:00",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "volume": 1000,
            }
        ]
        mock_get.return_value = mock_response

        eodhd_source = EodhdDataSource(api_key="test_key")
        result = eodhd_source.fetch("AAPL.US", "2024-01-01", "2024-01-02", "5m")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert list(result.columns) == ["open", "high", "low", "close", "volume"]
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

        # Verify intraday endpoint with Unix timestamps
        call_args = mock_get.call_args
        assert "eodhd.com/api/intraday/AAPL.US" in call_args[0][0]
        assert call_args[1]["params"]["interval"] == "5m"
        assert call_args[1]["params"]["from"] == str(
            int(pd.to_datetime("2024-01-01").timestamp())
        )
        assert call_args[1]["params"]["to"] == str(
            int(pd.to_datetime("2024-01-02").timestamp())
        )

    @patch("requests.Session.get")
    def test_fetch_data_with_intervals(self, mock_get: Mock) -> None:
        """Test data fetch with different EOD periods"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2023-01-01",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "adjusted_close": 100.5,
                "volume": 1000,
            }
        ]
        mock_get.return_value = mock_response

        eodhd_source = EodhdDataSource(api_key="test_key")

        # Weekly interval maps to period "w"
        eodhd_source.fetch("AAPL.US", "2023-01-01", "2023-01-02", "1wk")
        call_args = mock_get.call_args
        assert call_args[1]["params"]["period"] == "w"

        # Monthly interval maps to period "m"
        eodhd_source.fetch("AAPL.US", "2023-01-01", "2023-01-02", "1mo")
        call_args = mock_get.call_args
        assert call_args[1]["params"]["period"] == "m"

    @patch("requests.Session.get")
    def test_fetch_data_no_results(self, mock_get: Mock) -> None:
        """Test fetch when API returns no results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        eodhd_source = EodhdDataSource(api_key="test_key")

        with pytest.raises(RuntimeError, match="EODHD returned no results"):
            eodhd_source.fetch("INVALID.US", "2023-01-01", "2023-01-02")

    @patch("requests.Session.get")
    def test_fetch_data_http_error(self, mock_get: Mock) -> None:
        """Test fetch when API returns HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        eodhd_source = EodhdDataSource(api_key="invalid_key")

        with pytest.raises(RuntimeError, match="EODHD HTTP 401"):
            eodhd_source.fetch("AAPL.US", "2023-01-01", "2023-01-02")

    def test_fetch_unsupported_interval(self) -> None:
        """Test that unsupported interval raises ValueError"""
        eodhd_source = EodhdDataSource(api_key="test_key")
        with pytest.raises(ValueError, match="not supported for EODHD"):
            eodhd_source.fetch("AAPL.US", "2024-01-01", "2024-01-02", "15m")
