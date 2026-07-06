"""
Test DataFetch CLI

Tests the CLI interface for data downloading, including:
- Date validation
- Information flags (--list-datasources, --list-markets)
- Download requests via the service (mocked)
- ccxt exchange requirement
"""

from unittest.mock import Mock, patch

import argparse

import pandas as pd
import pytest


class TestValidateDateFormat:
    """Test date argument validation"""

    def test_valid_date(self) -> None:
        from connors_datafetch.cli import validate_date_format

        assert validate_date_format("2024-01-31") == "2024-01-31"

    def test_invalid_date_raises(self) -> None:
        from connors_datafetch.cli import validate_date_format

        with pytest.raises(argparse.ArgumentTypeError):
            validate_date_format("31/01/2024")

        with pytest.raises(argparse.ArgumentTypeError):
            validate_date_format("2024-13-01")


class TestDataFetchCLI:
    """Test DataFetch CLI functionality"""

    def test_import_cli_module(self) -> None:
        from connors_datafetch import cli

        assert hasattr(cli, "main")
        assert callable(cli.main)

    def _make_service(self) -> Mock:
        service = Mock()
        service.get_datasources.return_value = ["yfinance", "polygon", "ccxt"]
        service.get_market_configs.return_value = ["america", "australia"]
        service.get_available_timeframes.return_value = ["1M", "6M", "1Y"]
        service.get_timeframe_description.return_value = "1 Year"
        service.get_market_config_info.side_effect = lambda m: {
            "america": {"name": "United States", "yf_ticker_suffix": ""},
            "australia": {"name": "Australia", "yf_ticker_suffix": ".AX"},
        }.get(m)
        service.calculate_dates_from_timeframe.return_value = {
            "start": "2024-01-01",
            "end": "2024-12-31",
        }
        return service

    def _make_args(self, **overrides: object) -> Mock:
        args = Mock()
        args.list_datasources = False
        args.list_markets = False
        args.datasource = "yfinance"
        args.ticker = "AAPL"
        args.start = None
        args.end = None
        args.timespan = None
        args.interval = "1d"
        args.exchange = None
        args.market = None
        args.output = None
        args.format = "csv"
        args.include_datasource = False
        args.verbose = False
        for key, value in overrides.items():
            setattr(args, key, value)
        return args

    @patch("connors_datafetch.cli.DataFetchService")
    @patch("connors_datafetch.cli.argparse.ArgumentParser.parse_args")
    def test_cli_download(
        self, mock_parse_args: Mock, mock_service_class: Mock
    ) -> None:
        """A basic download defaults to the 1Y timespan and calls the service"""
        mock_parse_args.return_value = self._make_args()
        service = self._make_service()
        mock_service_class.return_value = service

        data = pd.DataFrame(
            {"close": [1.0, 2.0]},
            index=pd.date_range("2024-01-01", periods=2, freq="D"),
        )
        result = Mock(data=data, ticker="AAPL", file_path="/tmp/AAPL.csv")
        service.download_data.return_value = result

        from connors_datafetch.cli import main

        with patch("builtins.print"):
            main()

        service.download_data.assert_called_once()
        call_kwargs = service.download_data.call_args.kwargs
        assert call_kwargs["ticker"] == "AAPL"
        assert call_kwargs["datasource"] == "yfinance"
        # No dates and no timespan provided -> defaults to 1Y timespan
        assert call_kwargs["timeframe"] == "1Y"
        assert call_kwargs["start"] == "2024-01-01"
        assert call_kwargs["end"] == "2024-12-31"

    @patch("connors_datafetch.cli.DataFetchService")
    @patch("connors_datafetch.cli.argparse.ArgumentParser.parse_args")
    def test_cli_custom_date_range(
        self, mock_parse_args: Mock, mock_service_class: Mock
    ) -> None:
        """Explicit start/end dates are passed through without a timespan"""
        mock_parse_args.return_value = self._make_args(
            start="2023-01-01", end="2023-12-31"
        )
        service = self._make_service()
        mock_service_class.return_value = service

        data = pd.DataFrame(
            {"close": [1.0]},
            index=pd.date_range("2023-01-01", periods=1, freq="D"),
        )
        service.download_data.return_value = Mock(
            data=data, ticker="AAPL", file_path="/tmp/AAPL.csv"
        )

        from connors_datafetch.cli import main

        with patch("builtins.print"):
            main()

        call_kwargs = service.download_data.call_args.kwargs
        assert call_kwargs["start"] == "2023-01-01"
        assert call_kwargs["end"] == "2023-12-31"
        assert call_kwargs["timeframe"] is None

    @patch("connors_datafetch.cli.DataFetchService")
    @patch("connors_datafetch.cli.argparse.ArgumentParser.parse_args")
    def test_cli_list_datasources(
        self, mock_parse_args: Mock, mock_service_class: Mock
    ) -> None:
        mock_parse_args.return_value = self._make_args(list_datasources=True)
        service = self._make_service()
        mock_service_class.return_value = service

        from connors_datafetch.cli import main

        with patch("builtins.print") as mock_print:
            main()

        service.download_data.assert_not_called()
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "yfinance" in printed

    @patch("connors_datafetch.cli.DataFetchService")
    @patch("connors_datafetch.cli.argparse.ArgumentParser.parse_args")
    def test_cli_list_markets(
        self, mock_parse_args: Mock, mock_service_class: Mock
    ) -> None:
        mock_parse_args.return_value = self._make_args(list_markets=True)
        service = self._make_service()
        mock_service_class.return_value = service

        from connors_datafetch.cli import main

        with patch("builtins.print") as mock_print:
            main()

        service.download_data.assert_not_called()
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Australia" in printed

    @patch("connors_datafetch.cli.DataFetchService")
    @patch("connors_datafetch.cli.argparse.ArgumentParser.parse_args")
    def test_cli_ccxt_requires_exchange(
        self, mock_parse_args: Mock, mock_service_class: Mock
    ) -> None:
        """ccxt datasource without --exchange is a parser error"""
        mock_parse_args.return_value = self._make_args(datasource="ccxt")
        service = self._make_service()
        mock_service_class.return_value = service

        from connors_datafetch.cli import main

        with patch("builtins.print"), pytest.raises(SystemExit):
            main()

        service.download_data.assert_not_called()

    @patch("connors_datafetch.cli.DataFetchService")
    @patch("connors_datafetch.cli.argparse.ArgumentParser.parse_args")
    def test_cli_download_failure_is_reported(
        self, mock_parse_args: Mock, mock_service_class: Mock
    ) -> None:
        mock_parse_args.return_value = self._make_args(ticker="INVALID")
        service = self._make_service()
        mock_service_class.return_value = service
        service.download_data.side_effect = RuntimeError("No data for INVALID")

        from connors_datafetch.cli import main

        with patch("builtins.print") as mock_print:
            main()

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Download failed" in printed
        assert "No data for INVALID" in printed
