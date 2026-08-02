"""Alpaca Market Data API — US equities, daily and intraday.

Alpaca is primarily a brokerage, but it ships a separate Market Data API
(``data.alpaca.markets``) sourced from the CTA and UTP consolidated tapes, with
history back to 2016. That makes it this project's intraday equities source:
the other keyed providers either reject intraday on their current plan (EODHD
returns ``403 Only EOD data allowed for free users``) or cap it at a couple of
months (yfinance).

Two properties matter for session-based strategies such as the opening-range
breakout family, and both are why this source exists:

- **Timestamps are true UTC.** Alpaca returns RFC-3339 UTC (``13:30:00Z`` is
  the 09:30 New York open during EDT). yfinance intraday returns exchange-local
  times that get stamped UTC, which silently shifts every session boundary.
- **Feed choice changes the data's meaning.** ``sip`` is the full consolidated
  tape; ``iex`` is one venue at roughly 3% of consolidated volume. An opening
  range computed from IEX highs/lows is not the same range the market saw, so
  this module refuses to silently downgrade — see :meth:`fetch`.

Crypto is deliberately out of scope here; ``ccxt`` already covers it.
"""

import os
import warnings
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from connors_datafetch.core.registry import registry

BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"

#: Per-request bar cap imposed by the API; pagination continues past it.
PAGE_LIMIT = 10_000

#: Guard against an unbounded loop if the API ever returns a repeating token.
MAX_PAGES = 1_000


@registry.register_datasource("alpaca")
class AlpacaDataSource:
    """Alpaca Market Data — US equities OHLCV, daily and intraday.

    Requires ``ALPACA_API_KEY`` plus ``ALPACA_SECRET_KEY`` (``ALPACA_API_SECRET``
    is accepted as an alias). The ``sip`` feed needs a paid data plan; free
    Basic accounts must pass ``feed="iex"`` explicitly.

    Example:
        >>> ds = AlpacaDataSource()
        >>> df = ds.fetch("SPY", "2025-08-01", "2026-07-31", "5m")
    """

    #: CLI interval -> Alpaca ``timeframe``
    INTERVAL_MAP = {
        "1m": "1Min",
        "5m": "5Min",
        "15m": "15Min",
        "30m": "30Min",
        "1h": "1Hour",
        "2h": "2Hour",
        "4h": "4Hour",
        "1d": "1Day",
        "1wk": "1Week",
        "1mo": "1Month",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        feed: Optional[str] = None,
        adjustment: str = "all",
    ) -> None:
        """
        Args:
            api_key: Alpaca key id; falls back to ``ALPACA_API_KEY``.
            secret_key: Alpaca secret; falls back to ``ALPACA_SECRET_KEY``
                then ``ALPACA_API_SECRET``.
            feed: ``sip`` (consolidated tape, paid) or ``iex`` (single venue,
                free). Falls back to ``ALPACA_DATA_FEED``, then ``sip``.
            adjustment: ``all`` (default), ``split``, ``dividend`` or ``raw``.
                Backtests want split adjustment at minimum, or every historical
                split shows up as a fake gap.
        """
        self.session = requests.Session()

        api_key = api_key or os.getenv("ALPACA_API_KEY")
        secret_key = (
            secret_key
            or os.getenv("ALPACA_SECRET_KEY")
            or os.getenv("ALPACA_API_SECRET")
        )
        if not api_key or not secret_key:
            raise ValueError(
                "Alpaca API credentials are required. Set ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY environment variables, or pass api_key and "
                "secret_key parameters."
            )

        feed = feed or os.getenv("ALPACA_DATA_FEED") or "sip"
        if feed not in ("sip", "iex"):
            raise ValueError(f"feed must be 'sip' or 'iex', got {feed!r}")
        self.feed = feed

        valid_adjustments = ("raw", "split", "dividend", "all")
        if adjustment not in valid_adjustments:
            raise ValueError(
                f"adjustment must be one of {valid_adjustments}, got {adjustment!r}"
            )
        self.adjustment = adjustment

        self.session.headers.update(
            {"APCA-API-KEY-ID": api_key, "APCA-API-SECRET-KEY": secret_key}
        )

    def fetch(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV bars, following pagination to the end of the range.

        Raises rather than falling back to ``iex`` when the account is not
        entitled to ``sip``. A silent downgrade would swap the consolidated
        tape for ~3% of it while the caller still believed it had full-market
        highs and lows — the kind of substitution that quietly invalidates any
        session-range or volume-conditioned result.
        """
        timeframe = self.INTERVAL_MAP.get(interval)
        if timeframe is None:
            supported = ", ".join(sorted(self.INTERVAL_MAP))
            raise ValueError(
                f"Interval '{interval}' not supported for Alpaca datasource. "
                f"Supported intervals: {supported}"
            )

        base_params: Dict[str, Any] = {
            "symbols": symbol.upper(),
            "timeframe": timeframe,
            "start": _rfc3339(start),
            "end": _rfc3339(end),
            "limit": PAGE_LIMIT,
            "feed": self.feed,
            "adjustment": self.adjustment,
            "sort": "asc",
        }

        rows: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        for _ in range(MAX_PAGES):
            # A fresh dict per request: mutating one shared params dict makes
            # every call alias the same object, which hides the token actually
            # sent and would break any future retry/logging of a single request
            params = dict(base_params)
            if page_token:
                params["page_token"] = page_token
            response = self.session.get(BARS_URL, params=params, timeout=30)
            if response.status_code != 200:
                raise RuntimeError(self._error_message(response))

            payload = response.json()
            rows.extend(payload.get("bars", {}).get(symbol.upper(), []))

            page_token = payload.get("next_page_token")
            if not page_token:
                break
        else:
            warnings.warn(
                f"Alpaca pagination stopped at {MAX_PAGES} pages; "
                f"the result may be truncated.",
                stacklevel=2,
            )

        if not rows:
            raise RuntimeError(
                f"Alpaca returned no bars for {symbol} "
                f"({interval}, {start} to {end}, feed={self.feed})"
            )

        df = pd.DataFrame(rows)
        # t/o/h/l/c/v are Alpaca's field names; n (trade count) and vw (VWAP)
        # are dropped to keep the shared OHLCV schema
        df = df.rename(
            columns={
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
            }
        )
        df.index = pd.to_datetime(df["t"], utc=True, format="ISO8601")
        df.index.name = "date"
        df = df[["open", "high", "low", "close", "volume"]].sort_index()
        return df

    def _error_message(self, response: requests.Response) -> str:
        """Turn an API error into something actionable."""
        body = response.text[:200]
        if response.status_code in (401, 403) and self.feed == "sip":
            return (
                f"Alpaca HTTP {response.status_code}: {body}\n"
                "The 'sip' (consolidated tape) feed requires a paid Alpaca data "
                "plan. Either subscribe, or pass feed='iex' / set "
                "ALPACA_DATA_FEED=iex to use the free single-venue feed — but "
                "note IEX carries roughly 3% of consolidated volume, so opening "
                "ranges and volume filters computed from it will not match the "
                "market."
            )
        if response.status_code in (401, 403):
            return (
                f"Alpaca HTTP {response.status_code}: {body}\n"
                "Check ALPACA_API_KEY / ALPACA_SECRET_KEY."
            )
        return f"Alpaca HTTP {response.status_code}: {body}"


def _rfc3339(value: str) -> str:
    """Normalize a date or datetime to the RFC-3339 UTC string the API wants."""
    ts = pd.to_datetime(value, utc=True) if _has_tz(value) else pd.to_datetime(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return str(ts.strftime("%Y-%m-%dT%H:%M:%SZ"))


def _has_tz(value: str) -> bool:
    return isinstance(value, str) and (
        value.endswith("Z") or "+" in value[10:] or "-" in value[10:]
    )
