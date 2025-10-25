"""Tests for CCXT crypto datasource implementation"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from connors_datafetch.datasources.ccxt import CCXTDataSource


class TestCCXTDataSource:
    """Test CCXT crypto datasource"""

    def test_init_with_default_exchange(self) -> None:
        """Test initialization with default exchange (binance)"""
        with patch("ccxt.binance") as mock_exchange:
            mock_instance = MagicMock()
            mock_exchange.return_value = mock_instance

            ds = CCXTDataSource()

            assert ds.exchange_id == "binance"
            assert ds.exchange == mock_instance
            mock_exchange.assert_called_once()

    def test_init_with_custom_exchange(self) -> None:
        """Test initialization with custom exchange"""
        with patch("ccxt.kraken") as mock_exchange:
            mock_instance = MagicMock()
            mock_exchange.return_value = mock_instance

            ds = CCXTDataSource(exchange="kraken")

            assert ds.exchange_id == "kraken"
            assert ds.exchange == mock_instance
            mock_exchange.assert_called_once()

    def test_init_with_invalid_exchange_raises_error(self) -> None:
        """Test that initialization with invalid exchange raises ValueError"""
        with patch("ccxt.exchanges", ["binance", "kraken"]):
            with pytest.raises(ValueError, match="not supported by CCXT"):
                CCXTDataSource(exchange="invalid_exchange")

    def test_init_with_api_credentials(self) -> None:
        """Test initialization with API key and secret"""
        with patch("ccxt.binance") as mock_exchange:
            mock_instance = MagicMock()
            mock_exchange.return_value = mock_instance

            ds = CCXTDataSource(
                exchange="binance",
                api_key="test_api_key",
                secret="test_secret"
            )

            mock_exchange.assert_called_once_with({
                "apiKey": "test_api_key",
                "secret": "test_secret"
            })

    @patch.dict("os.environ", {"CCXT_API_KEY": "env_api_key", "CCXT_SECRET": "env_secret"})
    def test_init_with_env_credentials(self) -> None:
        """Test initialization with credentials from environment"""
        with patch("ccxt.binance") as mock_exchange:
            mock_instance = MagicMock()
            mock_exchange.return_value = mock_instance

            ds = CCXTDataSource(exchange="binance")

            mock_exchange.assert_called_once_with({
                "apiKey": "env_api_key",
                "secret": "env_secret"
            })

    def test_fetch_ohlcv_success(self) -> None:
        """Test successful OHLCV data fetch"""
        with patch("ccxt.binance") as mock_exchange_class:
            # Setup mock exchange
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange

            # Mock OHLCV data (timestamp, open, high, low, close, volume)
            mock_ohlcv = [
                [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 100.5],  # 2024-01-01 00:00
                [1704153600000, 42300.0, 42800.0, 42100.0, 42600.0, 95.3],   # 2024-01-02 00:00
                [1704240000000, 42600.0, 43000.0, 42400.0, 42800.0, 110.2],  # 2024-01-03 00:00
            ]
            mock_exchange.fetch_ohlcv.return_value = mock_ohlcv
            mock_exchange.timeframes = {"1d": "1d"}

            # Create datasource and fetch
            ds = CCXTDataSource(exchange="binance")
            result = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-03", "1d")

            # Assertions
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3
            assert list(result.columns) == ["open", "high", "low", "close", "volume"]
            assert result.index.name == "date"
            assert result["open"].iloc[0] == 42000.0
            assert result["close"].iloc[-1] == 42800.0

            # Verify exchange method was called correctly
            mock_exchange.fetch_ohlcv.assert_called()

    def test_fetch_with_pagination(self) -> None:
        """Test data fetch with pagination for large date ranges"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange

            # Mock two batches of data
            first_batch = [
                [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 100.5],
            ]
            second_batch = [
                [1704153600000, 42300.0, 42800.0, 42100.0, 42600.0, 95.3],
            ]

            # Return different data on successive calls
            mock_exchange.fetch_ohlcv.side_effect = [first_batch, second_batch, []]
            mock_exchange.timeframes = {"1d": "1d"}

            ds = CCXTDataSource(exchange="binance")
            result = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-02", "1d")

            # Should have made multiple calls due to pagination
            assert mock_exchange.fetch_ohlcv.call_count >= 2
            assert len(result) == 2

    def test_fetch_with_invalid_interval(self) -> None:
        """Test fetch with unsupported interval raises ValueError"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange

            ds = CCXTDataSource(exchange="binance")

            with pytest.raises(ValueError, match="not supported for CCXT"):
                ds.fetch("BTC/USDT", "2024-01-01", "2024-01-02", "invalid")

    def test_fetch_with_no_data_raises_error(self) -> None:
        """Test that fetch raises error when no data found"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange
            mock_exchange.fetch_ohlcv.return_value = []
            mock_exchange.timeframes = {"1d": "1d"}

            ds = CCXTDataSource(exchange="binance")

            with pytest.raises(RuntimeError, match="No data found"):
                ds.fetch("BTC/USDT", "2024-01-01", "2024-01-02", "1d")

    def test_fetch_with_network_error(self) -> None:
        """Test fetch handles network errors properly"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange
            mock_exchange.timeframes = {"1d": "1d"}

            # Import ccxt to access exceptions
            import ccxt as ccxt_module
            mock_exchange.fetch_ohlcv.side_effect = ccxt_module.NetworkError("Connection failed")

            ds = CCXTDataSource(exchange="binance")

            with pytest.raises(RuntimeError, match="Network error"):
                ds.fetch("BTC/USDT", "2024-01-01", "2024-01-02", "1d")

    def test_fetch_with_exchange_error(self) -> None:
        """Test fetch handles exchange errors properly"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange
            mock_exchange.timeframes = {"1d": "1d"}

            # Import ccxt to access exceptions
            import ccxt as ccxt_module
            mock_exchange.fetch_ohlcv.side_effect = ccxt_module.ExchangeError("Invalid symbol")

            ds = CCXTDataSource(exchange="binance")

            with pytest.raises(RuntimeError, match="Exchange error"):
                ds.fetch("INVALID/PAIR", "2024-01-01", "2024-01-02", "1d")

    def test_fetch_filters_date_range(self) -> None:
        """Test that fetch filters data to exact date range"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange

            # Mock data with dates outside range
            mock_ohlcv = [
                [1703980800000, 41000.0, 41500.0, 40800.0, 41300.0, 100.0],  # 2023-12-31
                [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 100.5],  # 2024-01-01
                [1704153600000, 42300.0, 42800.0, 42100.0, 42600.0, 95.3],   # 2024-01-02
                [1704240000000, 42600.0, 43000.0, 42400.0, 42800.0, 110.2],  # 2024-01-03
            ]
            mock_exchange.fetch_ohlcv.return_value = mock_ohlcv
            mock_exchange.timeframes = {"1d": "1d"}

            ds = CCXTDataSource(exchange="binance")
            result = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-02", "1d")

            # Should only include data within range
            assert len(result) == 2
            assert result.index[0].strftime("%Y-%m-%d") == "2024-01-01"
            assert result.index[-1].strftime("%Y-%m-%d") == "2024-01-02"

    def test_fetch_removes_duplicate_timestamps(self) -> None:
        """Test that fetch removes duplicate timestamps"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange

            # Mock data with duplicates
            mock_ohlcv = [
                [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 100.5],
                [1704067200000, 42100.0, 42600.0, 41900.0, 42400.0, 101.5],  # Duplicate
                [1704153600000, 42300.0, 42800.0, 42100.0, 42600.0, 95.3],
            ]
            mock_exchange.fetch_ohlcv.return_value = mock_ohlcv
            mock_exchange.timeframes = {"1d": "1d"}

            ds = CCXTDataSource(exchange="binance")
            result = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-02", "1d")

            # Should have removed duplicate
            assert len(result) == 2
            assert not result.index.duplicated().any()

    def test_interval_mapping(self) -> None:
        """Test that interval mapping works correctly"""
        assert CCXTDataSource.INTERVAL_MAP["1m"] == "1m"
        assert CCXTDataSource.INTERVAL_MAP["5m"] == "5m"
        assert CCXTDataSource.INTERVAL_MAP["1h"] == "1h"
        assert CCXTDataSource.INTERVAL_MAP["1d"] == "1d"
        assert CCXTDataSource.INTERVAL_MAP["1w"] == "1w"
        assert CCXTDataSource.INTERVAL_MAP["1M"] == "1M"

    def test_get_supported_symbols(self) -> None:
        """Test getting supported trading pairs"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange
            mock_exchange.markets = {
                "BTC/USDT": {},
                "ETH/USDT": {},
                "BNB/USDT": {}
            }

            ds = CCXTDataSource(exchange="binance")
            symbols = ds.get_supported_symbols()

            assert isinstance(symbols, list)
            assert "BTC/USDT" in symbols
            assert "ETH/USDT" in symbols
            assert len(symbols) == 3

    def test_get_supported_timeframes(self) -> None:
        """Test getting supported timeframes"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange
            mock_exchange.timeframes = {
                "1m": "1m",
                "5m": "5m",
                "1h": "1h",
                "1d": "1d"
            }

            ds = CCXTDataSource(exchange="binance")
            timeframes = ds.get_supported_timeframes()

            assert isinstance(timeframes, list)
            assert "1m" in timeframes
            assert "1h" in timeframes
            assert "1d" in timeframes

    def test_columns_are_lowercase(self) -> None:
        """Test that returned DataFrame has lowercase column names"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange
            mock_ohlcv = [
                [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 100.5],
            ]
            # Use side_effect to return data once, then empty to end loop
            mock_exchange.fetch_ohlcv.side_effect = [mock_ohlcv, []]
            mock_exchange.timeframes = {"1d": "1d"}

            ds = CCXTDataSource(exchange="binance")
            result = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-02", "1d")

            # All columns should be lowercase
            for col in result.columns:
                assert col == col.lower()

    def test_index_is_datetime(self) -> None:
        """Test that index is DatetimeIndex"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange
            mock_ohlcv = [
                [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 100.5],
            ]
            # Use side_effect to return data once, then empty to end loop
            mock_exchange.fetch_ohlcv.side_effect = [mock_ohlcv, []]
            mock_exchange.timeframes = {"1d": "1d"}

            ds = CCXTDataSource(exchange="binance")
            result = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-02", "1d")

            assert isinstance(result.index, pd.DatetimeIndex)
            assert result.index.name == "date"

    def test_data_is_sorted_by_date(self) -> None:
        """Test that returned data is sorted by date"""
        with patch("ccxt.binance") as mock_exchange_class:
            mock_exchange = MagicMock()
            mock_exchange_class.return_value = mock_exchange

            # Mock unsorted data
            mock_ohlcv = [
                [1704153600000, 42300.0, 42800.0, 42100.0, 42600.0, 95.3],   # 2024-01-02
                [1704067200000, 42000.0, 42500.0, 41800.0, 42300.0, 100.5],  # 2024-01-01
                [1704240000000, 42600.0, 43000.0, 42400.0, 42800.0, 110.2],  # 2024-01-03
            ]
            mock_exchange.fetch_ohlcv.return_value = mock_ohlcv
            mock_exchange.timeframes = {"1d": "1d"}

            ds = CCXTDataSource(exchange="binance")
            result = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-03", "1d")

            # Should be sorted ascending
            assert (result.index[:-1] <= result.index[1:]).all()


class TestCCXTIntervalMapping:
    """Test interval mapping for different crypto timeframes"""

    def test_all_intervals_mapped(self) -> None:
        """Test that all common crypto intervals are mapped"""
        intervals = CCXTDataSource.INTERVAL_MAP

        # Common crypto intervals
        assert "1m" in intervals
        assert "5m" in intervals
        assert "15m" in intervals
        assert "30m" in intervals
        assert "1h" in intervals
        assert "2h" in intervals
        assert "4h" in intervals
        assert "6h" in intervals
        assert "12h" in intervals
        assert "1d" in intervals
        assert "1w" in intervals
        assert "1M" in intervals
