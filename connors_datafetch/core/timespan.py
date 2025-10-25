"""
Timespan utilities for handling pre-defined date ranges
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd


class TimespanCalculator:
    """Calculate start and end dates based on timespan specifications"""

    PREDEFINED_TIMESPANS = {
        "1D": {"days": 1},
        "5D": {"days": 5},
        "10D": {"days": 10},
        "1W": {"weeks": 1},
        "2W": {"weeks": 2},
        "1M": {"days": 30},  # Approximate month
        "3M": {"days": 90},  # Approximate quarter
        "6M": {"days": 180},  # Approximate half year
        "YTD": "year_to_date",
        "1Y": {"days": 365},
        "2Y": {"days": 730},
        "3Y": {"days": 1095},
        "5Y": {"days": 1825},
    }

    @classmethod
    def calculate_dates(
        cls,
        timespan: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        end_date_override: Optional[datetime] = None,
    ) -> Tuple[str, str]:
        """
        Calculate start and end dates based on timespan or explicit dates.

        Args:
            timespan: Pre-defined timespan (e.g., "1Y", "6M", "YTD") or None for custom dates
            start_date: Custom start date in YYYY-MM-DD format
            end_date: Custom end date in YYYY-MM-DD format
            end_date_override: Override end date as datetime object (for testing)

        Returns:
            Tuple of (start_date, end_date) as strings in YYYY-MM-DD format

        Raises:
            ValueError: If timespan is invalid or dates are malformed
        """
        # Use provided end date override or default to today
        end_dt = end_date_override or datetime.now()

        # If both start and end dates are provided, use them directly
        if start_date and end_date:
            cls._validate_date_format(start_date)
            cls._validate_date_format(end_date)
            return start_date, end_date

        # If only start date is provided, use it with today as end
        if start_date and not end_date:
            cls._validate_date_format(start_date)
            return start_date, end_dt.strftime("%Y-%m-%d")

        # If only end date is provided, use 1Y timeframe with custom end
        if end_date and not start_date:
            cls._validate_date_format(end_date)
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            start_dt = end_dt - timedelta(days=365)  # Default 1Y lookback
            return start_dt.strftime("%Y-%m-%d"), end_date

        # Use timespan (default to 1Y if not specified)
        timespan = timespan or "1Y"

        if timespan not in cls.PREDEFINED_TIMESPANS:
            raise ValueError(
                f"Invalid timespan '{timespan}'. "
                f"Available options: {', '.join(cls.PREDEFINED_TIMESPANS.keys())}"
            )

        # Handle YTD special case
        if timespan == "YTD":
            start_dt = datetime(end_dt.year, 1, 1)
            return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

        # Handle standard timespans
        timespan_config = cls.PREDEFINED_TIMESPANS[timespan]
        start_dt = end_dt - timedelta(**timespan_config)

        return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

    @classmethod
    def _validate_date_format(cls, date_str: str) -> None:
        """Validate date string is in YYYY-MM-DD format"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid date format '{date_str}'. Expected YYYY-MM-DD format."
            ) from e

    @classmethod
    def get_available_timespans(cls) -> list[str]:
        """Get list of available predefined timespans"""
        return list(cls.PREDEFINED_TIMESPANS.keys())

    @classmethod
    def get_timespan_description(cls, timespan: str) -> str:
        """Get human-readable description of timespan"""
        descriptions = {
            "1D": "1 Day",
            "5D": "5 Days",
            "10D": "10 Days",
            "1W": "1 Week",
            "2W": "2 Weeks",
            "1M": "1 Month",
            "3M": "3 Months",
            "6M": "6 Months",
            "YTD": "Year to Date",
            "1Y": "1 Year",
            "2Y": "2 Years",
            "3Y": "3 Years",
            "5Y": "5 Years",
        }
        return descriptions.get(timespan, timespan)

    # Backwards compatibility aliases
    PREDEFINED_TIMEFRAMES = PREDEFINED_TIMESPANS

    @classmethod
    def get_available_timeframes(cls) -> list[str]:
        """Get list of available predefined timeframes (legacy alias)"""
        return cls.get_available_timespans()

    @classmethod
    def get_timeframe_description(cls, timeframe: str) -> str:
        """Get human-readable description of timeframe (legacy alias)"""
        return cls.get_timespan_description(timeframe)


# Backwards compatibility alias
TimeframeCalculator = TimespanCalculator
