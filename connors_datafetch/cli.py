"""
Dataset DataFetch CLI

A command-line interface for fetching financial data using available data sources.
Supports saving data as CSV or JSON files compatible with pandas DataFrame format.

Installed as the ``connors-datafetch`` console script; also runnable via
``python -m connors_datafetch.cli``.
"""

import argparse
from datetime import date, datetime
from typing import Optional

from connors_datafetch.services.datafetch_service import DataFetchService


def validate_date_format(date_str: str) -> str:
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Date '{date_str}' must be in YYYY-MM-DD format"
        )


def main() -> None:
    """Main entry point for the datafetch CLI"""

    # Initialize datafetch service
    datafetch_service = DataFetchService()

    # Get available datasources and markets from service
    available_datasources = datafetch_service.get_datasources()
    available_markets = datafetch_service.get_market_configs()

    parser = argparse.ArgumentParser(
        prog="connors-datafetch",
        description="Fetch financial data using available data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Download Apple stock data using default timespan (1 year)
  connors-datafetch --datasource yfinance --ticker AAPL

  # Download with predefined timespan
  connors-datafetch --datasource yfinance --ticker AAPL --timespan 6M

  # Download year-to-date data
  connors-datafetch --datasource yfinance --ticker AAPL --timespan YTD

  # Download with custom date range and interval
  connors-datafetch --datasource yfinance --ticker MSFT --start 2023-01-01 --end 2023-12-31 --interval 1wk --output weekly_msft.csv

  # Download as JSON format with 3-month timespan
  connors-datafetch --datasource yfinance --ticker AAPL --timespan 3M --format json --output aapl_data.json

  # Download Australian stock with market suffix (uses defaults: 1 year)
  connors-datafetch --datasource yfinance --ticker BHP --market australia --timespan 2Y

  # Download using Polygon.io datasource with timespan
  connors-datafetch --datasource polygon --ticker TSLA --timespan 1M

  # Download crypto data from Binance exchange
  connors-datafetch --datasource ccxt --exchange binance --ticker BTC/USDT --interval 1h --timespan 1M

  # Download crypto data from Kraken exchange
  connors-datafetch --datasource ccxt --exchange kraken --ticker ETH/USD --start 2024-01-01 --end 2024-12-31 --interval 1d

Available datasources: {', '.join(available_datasources)}
Available markets: {', '.join(available_markets)}
Available timespans: {', '.join(datafetch_service.get_available_timeframes())}
        """,
    )

    # List available datasources
    parser.add_argument(
        "--list-datasources",
        action="store_true",
        help="List all available datasources and exit",
    )

    # Required arguments (except when listing datasources)
    parser.add_argument(
        "--datasource",
        choices=available_datasources,
        help="Data source to use for downloading data",
    )

    parser.add_argument(
        "--ticker", help="Stock ticker symbol to download (e.g., AAPL, MSFT, TSLA)"
    )

    parser.add_argument(
        "--start",
        type=validate_date_format,
        help="Start date in YYYY-MM-DD format (default: 1 year ago from end date)",
    )

    parser.add_argument(
        "--end",
        type=validate_date_format,
        help="End date in YYYY-MM-DD format (default: today)",
    )

    # Get available timeframes from service
    available_timeframes = datafetch_service.get_available_timeframes()

    parser.add_argument(
        "--timespan",
        choices=available_timeframes,
        help=f"Pre-defined timespan instead of custom dates. Available: {', '.join(available_timeframes)}",
    )

    # Optional arguments
    parser.add_argument(
        "--interval",
        default="1d",
        choices=[
            "1m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "12h",
            "1d",
            "1wk",
            "1mo",
            "1M",
        ],
        help="Data interval. Crypto supports: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M. Stocks support: 1d, 1wk, 1mo. Default: 1d",
    )

    parser.add_argument(
        "--exchange",
        help="Exchange for crypto datasource (e.g., binance, kraken, coinbase). Required when using --datasource ccxt",
    )

    parser.add_argument(
        "--market",
        choices=available_markets,
        help="Market configuration to apply ticker suffix (e.g., australia, brazil, japan)",
    )

    parser.add_argument(
        "--output",
        help="Output filename. If not specified, auto-generates based on parameters",
    )

    parser.add_argument(
        "--format",
        default="csv",
        choices=["csv", "json"],
        help="Output format: csv (default) or json",
    )

    parser.add_argument(
        "--include-datasource",
        action="store_true",
        default=False,
        help="Include datasource name in the filename (default: false)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed information",
    )

    # List markets
    parser.add_argument(
        "--list-markets",
        action="store_true",
        help="List all available market configurations and exit",
    )

    args = parser.parse_args()

    # Handle list datasources
    if args.list_datasources:
        print("📋 Available datasources:")
        for ds in available_datasources:
            print(f"  - {ds}")
        return

    # Handle list markets
    if args.list_markets:
        print("🌍 Available market configurations:")
        for market in available_markets:
            config_info = datafetch_service.get_market_config_info(market)
            if config_info:
                suffix_info = (
                    f" (suffix: {config_info['yf_ticker_suffix']})"
                    if config_info["yf_ticker_suffix"]
                    else " (no suffix)"
                )
                print(f"  - {market}: {config_info['name']}{suffix_info}")
        return

    # Check required arguments when not listing
    if not args.datasource:
        parser.error("--datasource is required")
    if not args.ticker:
        parser.error("--ticker is required")

    # Get date range - use timeframe or custom dates
    # Default to 1Y timespan if no timespan or dates provided
    if not args.timespan and not (args.start and args.end):
        args.timespan = "1Y"

    if args.timespan:
        # Calculate dates from timespan
        date_result = datafetch_service.calculate_dates_from_timeframe(
            timeframe=args.timespan, start_date=args.start, end_date=args.end
        )
        final_start = date_result["start"]
        final_end = date_result["end"]
    else:
        # Custom date range provided
        final_start = args.start
        final_end = args.end

    # Progress callback for verbose mode
    def progress_callback(message: str) -> None:
        if args.verbose:
            print(f"📊 {message}")

    # Validate exchange parameter for ccxt datasource
    if args.datasource == "ccxt" and not args.exchange:
        parser.error("--exchange is required when using --datasource ccxt")

    print(f"🔍 Downloading {args.ticker} data using {args.datasource} datasource")
    if args.exchange:
        print(f"🏦 Exchange: {args.exchange}")
    if args.timespan:
        timespan_desc = datafetch_service.get_timeframe_description(args.timespan)
        print(f"📅 Timespan: {args.timespan} ({timespan_desc})")
    print(f"📅 Period: {final_start} to {final_end}")
    print(f"⏱️  Interval: {args.interval}")
    if args.market:
        market_info = datafetch_service.get_market_config_info(args.market)
        if market_info:
            print(f"🌍 Market: {market_info['name']}")

    # Download data using service
    try:
        result = datafetch_service.download_data(
            datasource=args.datasource,
            ticker=args.ticker,
            start=final_start,
            end=final_end,
            interval=args.interval,
            market=args.market,
            output_file=args.output,
            output_format=args.format,
            timeframe=args.timespan,
            exchange=args.exchange,
            include_datasource=args.include_datasource,
            progress_callback=progress_callback if args.verbose else None,
        )

        # Print results
        if args.verbose:
            print(f"✅ Retrieved {len(result.data)} data points")
            print(
                f"📈 Date range: {result.data.index.min()} to {result.data.index.max()}"
            )
            print(f"📊 Columns: {', '.join(result.data.columns)}")
            print(f"💾 Data saved to: {result.file_path}")
            from pathlib import Path

            print(f"📁 File size: {Path(result.file_path).stat().st_size:,} bytes")
        else:
            print(f"✅ Downloaded {len(result.data)} records for {result.ticker}")
            from pathlib import Path

            print(f"💾 Saved to: {Path(result.file_path).name}")

    except Exception as e:
        print(f"❌ Download failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
