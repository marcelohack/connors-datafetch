"""Tests for the Alpaca Market Data datasource.

The behaviours worth pinning are the ones that would silently corrupt a
session-based backtest rather than raise: pagination dropping bars, UTC
timestamps being mangled, and a ``sip`` entitlement failure quietly degrading
to the single-venue ``iex`` feed.
"""

import os
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from connors_datafetch.datasources.alpaca import AlpacaDataSource

CREDS = {"ALPACA_API_KEY": "key-id", "ALPACA_SECRET_KEY": "secret"}


def bar(ts: str, close: float = 100.0, volume: int = 1_000) -> Dict[str, Any]:
    """One Alpaca bar payload (their field names)."""
    return {
        "t": ts,
        "o": close - 1,
        "h": close + 1,
        "l": close - 2,
        "c": close,
        "v": volume,
        "n": 10,
        "vw": close,
    }


def response(bars: List[Dict[str, Any]], token: Any = None, status: int = 200) -> Mock:
    r = Mock()
    r.status_code = status
    r.text = ""
    r.json.return_value = {"bars": {"SPY": bars}, "next_page_token": token}
    return r


@pytest.fixture
def source() -> AlpacaDataSource:
    with patch.dict(os.environ, CREDS, clear=False):
        return AlpacaDataSource(feed="sip")


class TestCredentials:
    def test_reads_credentials_from_environment(self) -> None:
        with patch.dict(os.environ, CREDS, clear=False):
            ds = AlpacaDataSource()
        assert ds.session.headers["APCA-API-KEY-ID"] == "key-id"
        assert ds.session.headers["APCA-API-SECRET-KEY"] == "secret"

    def test_accepts_the_api_secret_alias(self) -> None:
        env = {"ALPACA_API_KEY": "key-id", "ALPACA_API_SECRET": "alias-secret"}
        with patch.dict(os.environ, env, clear=True):
            ds = AlpacaDataSource()
        assert ds.session.headers["APCA-API-SECRET-KEY"] == "alias-secret"

    def test_missing_credentials_raise(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ALPACA_API_KEY"):
                AlpacaDataSource()

    @pytest.mark.parametrize("feed", ["nasdaq", "SIP ", "IEX"])
    def test_rejects_unknown_feed(self, feed: str) -> None:
        with patch.dict(os.environ, CREDS, clear=False):
            with pytest.raises(ValueError, match="feed must be"):
                AlpacaDataSource(feed=feed)

    def test_empty_feed_is_treated_as_unset(self) -> None:
        """`feed=""` means "not specified", so it resolves like `feed=None`."""
        with patch.dict(os.environ, CREDS, clear=True):
            assert AlpacaDataSource(feed="").feed == "sip"

    def test_rejects_unknown_adjustment(self) -> None:
        with patch.dict(os.environ, CREDS, clear=False):
            with pytest.raises(ValueError, match="adjustment must be"):
                AlpacaDataSource(adjustment="unadjusted")

    def test_feed_falls_back_to_env_then_sip(self) -> None:
        with patch.dict(os.environ, {**CREDS, "ALPACA_DATA_FEED": "iex"}, clear=False):
            assert AlpacaDataSource().feed == "iex"
        with patch.dict(os.environ, CREDS, clear=True):
            assert AlpacaDataSource().feed == "sip"


class TestFetch:
    def test_returns_the_shared_ohlcv_schema(self, source: AlpacaDataSource) -> None:
        with patch.object(
            source.session, "get", return_value=response([bar("2025-08-01T13:30:00Z")])
        ):
            df = source.fetch("SPY", "2025-08-01", "2025-08-02", "5m")

        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert df.index.name == "date"
        assert isinstance(df.index, pd.DatetimeIndex)
        # Alpaca's n (trade count) and vw (VWAP) are dropped
        assert "n" not in df.columns and "vw" not in df.columns

    def test_timestamps_stay_utc(self, source: AlpacaDataSource) -> None:
        """13:30Z is the 09:30 New York open during EDT. If this ever comes
        back naive or shifted, every session boundary moves."""
        with patch.object(
            source.session, "get", return_value=response([bar("2025-08-01T13:30:00Z")])
        ):
            df = source.fetch("SPY", "2025-08-01", "2025-08-02", "5m")

        assert str(df.index.tz) == "UTC"
        assert df.index[0] == pd.Timestamp("2025-08-01T13:30:00Z")
        ny = df.index.tz_convert("America/New_York")
        assert ny[0].strftime("%H:%M") == "09:30"

    def test_follows_pagination_and_keeps_every_bar(
        self, source: AlpacaDataSource
    ) -> None:
        pages = [
            response([bar("2025-08-01T13:30:00Z")], token="p2"),
            response([bar("2025-08-01T13:35:00Z")], token="p3"),
            response([bar("2025-08-01T13:40:00Z")], token=None),
        ]
        with patch.object(source.session, "get", side_effect=pages) as get:
            df = source.fetch("SPY", "2025-08-01", "2025-08-02", "5m")

        assert len(df) == 3
        assert get.call_count == 3
        # Page 2 and 3 must carry the token forward
        assert get.call_args_list[1].kwargs["params"]["page_token"] == "p2"
        assert get.call_args_list[2].kwargs["params"]["page_token"] == "p3"

    def test_result_is_sorted_by_timestamp(self, source: AlpacaDataSource) -> None:
        out_of_order = [bar("2025-08-01T13:40:00Z"), bar("2025-08-01T13:30:00Z")]
        with patch.object(source.session, "get", return_value=response(out_of_order)):
            df = source.fetch("SPY", "2025-08-01", "2025-08-02", "5m")
        assert df.index.is_monotonic_increasing

    def test_request_carries_feed_and_adjustment(
        self, source: AlpacaDataSource
    ) -> None:
        with patch.object(
            source.session, "get", return_value=response([bar("2025-08-01T13:30:00Z")])
        ) as get:
            source.fetch("SPY", "2025-08-01", "2025-08-02", "5m")

        params = get.call_args.kwargs["params"]
        assert params["feed"] == "sip"
        assert params["adjustment"] == "all"
        assert params["timeframe"] == "5Min"
        assert params["symbols"] == "SPY"
        assert params["start"] == "2025-08-01T00:00:00Z"

    def test_symbol_is_upper_cased(self, source: AlpacaDataSource) -> None:
        with patch.object(
            source.session, "get", return_value=response([bar("2025-08-01T13:30:00Z")])
        ) as get:
            source.fetch("spy", "2025-08-01", "2025-08-02", "5m")
        assert get.call_args.kwargs["params"]["symbols"] == "SPY"

    @pytest.mark.parametrize(
        "interval,timeframe",
        [("1m", "1Min"), ("5m", "5Min"), ("1h", "1Hour"), ("1d", "1Day")],
    )
    def test_interval_mapping(
        self, source: AlpacaDataSource, interval: str, timeframe: str
    ) -> None:
        with patch.object(
            source.session, "get", return_value=response([bar("2025-08-01T13:30:00Z")])
        ) as get:
            source.fetch("SPY", "2025-08-01", "2025-08-02", interval)
        assert get.call_args.kwargs["params"]["timeframe"] == timeframe

    def test_unsupported_interval_raises(self, source: AlpacaDataSource) -> None:
        with pytest.raises(ValueError, match="not supported"):
            source.fetch("SPY", "2025-08-01", "2025-08-02", "3s")

    def test_empty_result_raises_rather_than_returning_nothing(
        self, source: AlpacaDataSource
    ) -> None:
        with patch.object(source.session, "get", return_value=response([])):
            with pytest.raises(RuntimeError, match="no bars"):
                source.fetch("SPY", "2025-08-01", "2025-08-02", "5m")


class TestErrors:
    def test_sip_entitlement_failure_explains_the_iex_tradeoff(
        self, source: AlpacaDataSource
    ) -> None:
        """It must not silently downgrade to iex: that swaps the consolidated
        tape for ~3% of it while the caller still believes it has full-market
        highs and lows."""
        with patch.object(source.session, "get", return_value=response([], status=403)):
            with pytest.raises(RuntimeError) as excinfo:
                source.fetch("SPY", "2025-08-01", "2025-08-02", "5m")

        message = str(excinfo.value)
        assert "paid Alpaca data plan" in message
        assert "ALPACA_DATA_FEED=iex" in message
        assert "3%" in message

    def test_auth_failure_on_iex_points_at_the_credentials(self) -> None:
        with patch.dict(os.environ, CREDS, clear=False):
            ds = AlpacaDataSource(feed="iex")
        with patch.object(ds.session, "get", return_value=response([], status=401)):
            with pytest.raises(RuntimeError, match="ALPACA_API_KEY"):
                ds.fetch("SPY", "2025-08-01", "2025-08-02", "5m")

    def test_other_http_errors_surface_the_status(
        self, source: AlpacaDataSource
    ) -> None:
        with patch.object(source.session, "get", return_value=response([], status=500)):
            with pytest.raises(RuntimeError, match="Alpaca HTTP 500"):
                source.fetch("SPY", "2025-08-01", "2025-08-02", "5m")


class TestRegistration:
    def test_registered_under_the_alpaca_name(self) -> None:
        from connors_datafetch.core.registry import registry

        assert "alpaca" in registry.list_datasources()
