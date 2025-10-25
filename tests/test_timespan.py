"""
Tests for timespan utilities
"""

from datetime import date, datetime

import pytest

from connors_datafetch.core.timespan import TimespanCalculator, TimeframeCalculator


class TestTimespanCalculator:
    """Test cases for TimespanCalculator"""

    def test_get_available_timespans(self):
        """Test that all expected timespans are available"""
        timespans = TimespanCalculator.get_available_timespans()
        expected = [
            "1D",
            "5D",
            "10D",
            "1W",
            "2W",
            "1M",
            "3M",
            "6M",
            "YTD",
            "1Y",
            "2Y",
            "3Y",
            "5Y",
        ]
        assert timespans == expected

    def test_get_timespan_description(self):
        """Test timespan descriptions"""
        assert TimespanCalculator.get_timespan_description("1D") == "1 Day"
        assert TimespanCalculator.get_timespan_description("1Y") == "1 Year"
        assert TimespanCalculator.get_timespan_description("YTD") == "Year to Date"
        assert TimespanCalculator.get_timespan_description("6M") == "6 Months"

    def test_calculate_dates_with_custom_dates(self):
        """Test calculation with explicit start and end dates"""
        start, end = TimespanCalculator.calculate_dates(
            start_date="2023-01-01", end_date="2023-12-31"
        )
        assert start == "2023-01-01"
        assert end == "2023-12-31"

    def test_calculate_dates_with_only_start_date(self):
        """Test calculation with only start date provided"""
        # Use fixed end date for testing
        test_end = datetime(2024, 6, 15)
        start, end = TimespanCalculator.calculate_dates(
            start_date="2023-01-01", end_date_override=test_end
        )
        assert start == "2023-01-01"
        assert end == "2024-06-15"

    def test_calculate_dates_with_only_end_date(self):
        """Test calculation with only end date provided (defaults to 1Y lookback)"""
        start, end = TimespanCalculator.calculate_dates(end_date="2024-06-15")
        assert start == "2023-06-16"  # 365 days before (timedelta calculation)
        assert end == "2024-06-15"

    def test_calculate_dates_1y_timespan(self):
        """Test 1Y timespan calculation"""
        test_end = datetime(2024, 6, 15)
        start, end = TimespanCalculator.calculate_dates(
            timespan="1Y", end_date_override=test_end
        )
        assert start == "2023-06-16"  # 365 days before (timedelta calculation)
        assert end == "2024-06-15"

    def test_calculate_dates_6m_timespan(self):
        """Test 6M timespan calculation"""
        test_end = datetime(2024, 6, 15)
        start, end = TimespanCalculator.calculate_dates(
            timespan="6M", end_date_override=test_end
        )
        assert start == "2023-12-18"  # Approximately 6 months (180 days) before
        assert end == "2024-06-15"

    def test_calculate_dates_ytd_timespan(self):
        """Test YTD timespan calculation"""
        test_end = datetime(2024, 6, 15)
        start, end = TimespanCalculator.calculate_dates(
            timespan="YTD", end_date_override=test_end
        )
        assert start == "2024-01-01"
        assert end == "2024-06-15"

    def test_calculate_dates_1d_timespan(self):
        """Test 1D timespan calculation"""
        test_end = datetime(2024, 6, 15)
        start, end = TimespanCalculator.calculate_dates(
            timespan="1D", end_date_override=test_end
        )
        assert start == "2024-06-14"
        assert end == "2024-06-15"

    def test_calculate_dates_1w_timespan(self):
        """Test 1W timespan calculation"""
        test_end = datetime(2024, 6, 15)  # Saturday
        start, end = TimespanCalculator.calculate_dates(
            timespan="1W", end_date_override=test_end
        )
        assert start == "2024-06-08"  # 7 days before
        assert end == "2024-06-15"

    def test_calculate_dates_default_timespan(self):
        """Test default timespan (1Y) when no timespan specified"""
        test_end = datetime(2024, 6, 15)
        start, end = TimespanCalculator.calculate_dates(end_date_override=test_end)
        assert start == "2023-06-16"  # Default 1Y (365 days before)
        assert end == "2024-06-15"

    def test_calculate_dates_with_timespan_and_custom_start(self):
        """Test timespan with custom start date override"""
        test_end = datetime(2024, 6, 15)
        start, end = TimespanCalculator.calculate_dates(
            timespan="6M", start_date="2023-01-01", end_date_override=test_end
        )
        assert start == "2023-01-01"  # Custom start overrides timespan calculation
        assert end == "2024-06-15"

    def test_calculate_dates_with_timespan_and_custom_end(self):
        """Test timespan with custom end date override"""
        start, end = TimespanCalculator.calculate_dates(
            timespan="1Y", end_date="2023-12-31"
        )
        assert start == "2022-12-31"  # 1 year before custom end
        assert end == "2023-12-31"

    def test_calculate_dates_invalid_timespan(self):
        """Test error handling for invalid timespan"""
        with pytest.raises(ValueError, match="Invalid timespan 'INVALID'"):
            TimespanCalculator.calculate_dates(timespan="INVALID")

    def test_validate_date_format_valid(self):
        """Test date format validation with valid dates"""
        # Should not raise exception
        TimespanCalculator._validate_date_format("2023-01-01")
        TimespanCalculator._validate_date_format("2024-12-31")

    def test_validate_date_format_invalid(self):
        """Test date format validation with invalid dates"""
        with pytest.raises(ValueError, match="Invalid date format"):
            TimespanCalculator._validate_date_format("01/01/2023")

        with pytest.raises(ValueError, match="Invalid date format"):
            TimespanCalculator._validate_date_format("2023-13-01")

        with pytest.raises(ValueError, match="Invalid date format"):
            TimespanCalculator._validate_date_format("invalid-date")

    def test_calculate_dates_edge_cases(self):
        """Test edge cases for date calculations"""
        # Leap year handling - 365 days before Feb 29, 2024
        test_end = datetime(2024, 2, 29)  # Leap year
        start, end = TimespanCalculator.calculate_dates(
            timespan="1Y", end_date_override=test_end
        )
        assert start == "2023-03-01"  # 365 days before Feb 29, 2024
        assert end == "2024-02-29"

    def test_calculate_dates_year_boundary(self):
        """Test YTD calculation across year boundaries"""
        # Test early in year
        test_end = datetime(2024, 1, 5)
        start, end = TimespanCalculator.calculate_dates(
            timespan="YTD", end_date_override=test_end
        )
        assert start == "2024-01-01"
        assert end == "2024-01-05"

        # Test late in year
        test_end = datetime(2024, 12, 25)
        start, end = TimespanCalculator.calculate_dates(
            timespan="YTD", end_date_override=test_end
        )
        assert start == "2024-01-01"
        assert end == "2024-12-25"

    def test_all_predefined_timespans(self):
        """Test all predefined timespans work correctly"""
        test_end = datetime(2024, 6, 15)

        # Test that all timespans can be calculated without error
        for timeframe in TimespanCalculator.get_available_timeframes():
            start, end = TimespanCalculator.calculate_dates(
                timespan=timeframe, end_date_override=test_end
            )

            # Basic sanity checks
            assert isinstance(start, str)
            assert isinstance(end, str)
            assert start <= end  # Start should be before or equal to end
            assert end == "2024-06-15"  # End should match our test date

            # Validate date formats
            TimespanCalculator._validate_date_format(start)
            TimespanCalculator._validate_date_format(end)

    def test_timespan_period_validation(self):
        """Test that calculated periods make sense for each timespan"""
        test_end = datetime(2024, 6, 15)

        # Test approximate durations (allowing for some calendar variation)
        test_cases = [
            ("1D", 1, 1),  # Exactly 1 day
            ("5D", 5, 5),  # Exactly 5 days
            ("10D", 10, 10),  # Exactly 10 days
            ("1W", 7, 7),  # Exactly 7 days
            ("2W", 14, 14),  # Exactly 14 days
            ("1M", 28, 32),  # Approximately 1 month (28-32 days)
            ("3M", 88, 92),  # Approximately 3 months (88-92 days)
            ("6M", 178, 182),  # Approximately 6 months (178-182 days)
            ("1Y", 364, 366),  # Approximately 1 year (accounting for leap years)
            ("2Y", 728, 732),  # Approximately 2 years
        ]

        for timeframe, min_days, max_days in test_cases:
            start, end = TimespanCalculator.calculate_dates(
                timespan=timeframe, end_date_override=test_end
            )

            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            actual_days = (end_date - start_date).days

            assert (
                min_days <= actual_days <= max_days
            ), f"Timeframe {timeframe}: expected {min_days}-{max_days} days, got {actual_days}"


class TestBackwardsCompatibility:
    """Test backwards compatibility with timeframe terminology"""

    def test_timespan_calculator_alias(self):
        """Test that TimeframeCalculator alias works"""
        # Test that the alias exists and works
        assert TimeframeCalculator == TimespanCalculator

        # Test that old methods work
        timeframes = TimeframeCalculator.get_available_timeframes()
        assert timeframes == TimespanCalculator.get_available_timespans()

        desc = TimeframeCalculator.get_timeframe_description("1Y")
        assert desc == TimespanCalculator.get_timespan_description("1Y")

    def test_legacy_method_compatibility(self):
        """Test that legacy methods on TimespanCalculator work"""
        # Test legacy methods exist and work
        timeframes = TimespanCalculator.get_available_timeframes()
        timespans = TimespanCalculator.get_available_timespans()
        assert timeframes == timespans

        desc1 = TimespanCalculator.get_timeframe_description("1Y")
        desc2 = TimespanCalculator.get_timespan_description("1Y")
        assert desc1 == desc2
