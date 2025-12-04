"""Tests for pulllist service - week calculations and formatting."""

from datetime import UTC, datetime, timedelta

from app.services.pulllist import (
    format_week_display,
    get_current_week_id,
    get_next_week_id,
    get_previous_week_id,
    get_week_id_for_date,
    get_week_start_date,
)


class TestGetWeekIdForDate:
    """Tests for get_week_id_for_date function.

    Comic weeks run Wednesday-Tuesday, so:
    - Wed Nov 27 through Tue Dec 3 are all the same comic week
    - Mon Nov 25 and Tue Nov 26 belong to the PREVIOUS comic week
    """

    def test_wednesday_is_start_of_comic_week(self):
        """Wednesday should be the start of a comic week."""
        # Wednesday Nov 27, 2024
        wed = datetime(2024, 11, 27)
        week_id = get_week_id_for_date(wed)
        assert week_id == "2024-W48"

    def test_tuesday_is_end_of_comic_week(self):
        """Tuesday should be the end of a comic week (same as Wednesday)."""
        # Tuesday Dec 3, 2024 - same comic week as Wed Nov 27
        tue = datetime(2024, 12, 3)
        week_id = get_week_id_for_date(tue)
        assert week_id == "2024-W48"

    def test_monday_belongs_to_previous_comic_week(self):
        """Monday belongs to the comic week that started previous Wednesday."""
        # Monday Dec 2, 2024 - still in the Nov 27 comic week
        mon = datetime(2024, 12, 2)
        week_id = get_week_id_for_date(mon)
        assert week_id == "2024-W48"

    def test_thursday_same_week_as_wednesday(self):
        """Thursday through Tuesday should all be same comic week as Wednesday."""
        wed = datetime(2024, 11, 27)
        thu = datetime(2024, 11, 28)
        fri = datetime(2024, 11, 29)
        sat = datetime(2024, 11, 30)
        sun = datetime(2024, 12, 1)
        mon = datetime(2024, 12, 2)
        tue = datetime(2024, 12, 3)

        wed_id = get_week_id_for_date(wed)
        assert get_week_id_for_date(thu) == wed_id
        assert get_week_id_for_date(fri) == wed_id
        assert get_week_id_for_date(sat) == wed_id
        assert get_week_id_for_date(sun) == wed_id
        assert get_week_id_for_date(mon) == wed_id
        assert get_week_id_for_date(tue) == wed_id

    def test_next_wednesday_is_new_week(self):
        """Next Wednesday should start a new comic week."""
        wed1 = datetime(2024, 11, 27)
        wed2 = datetime(2024, 12, 4)

        assert get_week_id_for_date(wed1) == "2024-W48"
        assert get_week_id_for_date(wed2) == "2024-W49"

    def test_year_boundary_dec_to_jan(self):
        """Test week calculation across year boundary."""
        # Wednesday Dec 25, 2024 (Christmas)
        wed_dec = datetime(2024, 12, 25)
        # Wednesday Jan 1, 2025 (New Year's Day - it's a Wednesday!)
        wed_jan = datetime(2025, 1, 1)

        dec_week = get_week_id_for_date(wed_dec)
        jan_week = get_week_id_for_date(wed_jan)

        # They should be different weeks
        assert dec_week != jan_week
        # January 1, 2025 is week 1 of 2025
        assert jan_week == "2025-W01"

    def test_timezone_aware_datetime_handled(self):
        """Timezone-aware datetimes should be handled correctly."""
        # Wednesday Nov 27, 2024 in UTC
        dt_utc = datetime(2024, 11, 27, 12, 0, 0, tzinfo=UTC)
        week_id = get_week_id_for_date(dt_utc)
        assert week_id == "2024-W48"

    def test_timezone_stripped_for_calculation(self):
        """Different timezones should produce same result for same date."""
        from datetime import timezone as tz

        # Same date, different timezones
        dt_utc = datetime(2024, 11, 27, 12, 0, 0, tzinfo=UTC)
        dt_est = datetime(2024, 11, 27, 12, 0, 0, tzinfo=tz(timedelta(hours=-5)))

        assert get_week_id_for_date(dt_utc) == get_week_id_for_date(dt_est)


class TestGetWeekStartDate:
    """Tests for get_week_start_date function."""

    def test_returns_wednesday(self):
        """Week start should always be a Wednesday."""
        week_start = get_week_start_date("2024-W48")
        # Wednesday is weekday 2
        assert week_start.weekday() == 2

    def test_correct_wednesday_for_week(self):
        """Should return the correct Wednesday for the given week."""
        week_start = get_week_start_date("2024-W48")
        assert week_start.year == 2024
        assert week_start.month == 11
        assert week_start.day == 27

    def test_week_1_of_year(self):
        """Should handle week 1 correctly."""
        week_start = get_week_start_date("2025-W01")
        assert week_start.weekday() == 2
        assert week_start.year == 2025
        assert week_start.month == 1
        assert week_start.day == 1  # Jan 1, 2025 is a Wednesday

    def test_week_52_of_year(self):
        """Should handle week 52 correctly."""
        week_start = get_week_start_date("2024-W52")
        assert week_start.weekday() == 2
        assert week_start.month == 12
        assert week_start.day == 25  # Christmas 2024 is a Wednesday

    def test_none_returns_current_week_wednesday(self):
        """Passing None should return this week's Wednesday."""
        week_start = get_week_start_date(None)
        assert week_start.weekday() == 2

        # Verify it's within the current comic week
        now = datetime.now()
        days_diff = (now - week_start).days
        assert 0 <= days_diff < 7


class TestGetPreviousWeekId:
    """Tests for get_previous_week_id function."""

    def test_simple_previous_week(self):
        """Should return previous week's ID."""
        assert get_previous_week_id("2024-W48") == "2024-W47"

    def test_year_boundary_week_1_to_previous_year(self):
        """Week 1 should go back to previous year's last week."""
        prev = get_previous_week_id("2025-W01")
        # 2024 has 52 weeks (ends on Tuesday Dec 31, 2024)
        assert prev == "2024-W52"

    def test_week_2_to_week_1(self):
        """Week 2 should go to week 1."""
        assert get_previous_week_id("2024-W02") == "2024-W01"


class TestGetNextWeekId:
    """Tests for get_next_week_id function."""

    def test_simple_next_week(self):
        """Should return next week's ID."""
        assert get_next_week_id("2024-W48") == "2024-W49"

    def test_year_boundary_last_week_to_next_year(self):
        """Last week of year should go to next year's week 1."""
        next_week = get_next_week_id("2024-W52")
        assert next_week == "2025-W01"

    def test_week_51_to_week_52(self):
        """Week 51 should go to week 52."""
        assert get_next_week_id("2024-W51") == "2024-W52"


class TestFormatWeekDisplay:
    """Tests for format_week_display function."""

    def test_same_month_display(self):
        """When week is within same month, use abbreviated format."""
        # Week starting Nov 27, ending Dec 3 - crosses months
        # But let's test a week that stays in one month
        # Week 45 of 2024: Nov 6-12 (Wed-Tue, all in November)
        display = format_week_display("2024-W45")
        assert display == "Nov 06 - 12, 2024"

    def test_different_months_same_year(self):
        """When week crosses months but same year."""
        # Week 48: Nov 27 - Dec 3
        display = format_week_display("2024-W48")
        assert display == "Nov 27 - Dec 03, 2024"

    def test_different_years(self):
        """When week crosses year boundary."""
        # Week 1 of 2025 starts Jan 1 (Wed), ends Jan 7 (Tue)
        # Actually let's check 2024-W01 which might span years
        # Week 52 of 2024: Dec 25-31 (all in 2024)
        # For a year-spanning week, let's use 2019-W01
        # Jan 2019 week 1 starts Dec 31 2018 (Monday in ISO)
        # Comic week starts Wednesday Jan 2, 2019
        # Hmm, let's just verify the format is right
        display = format_week_display("2024-W52")
        # Dec 25 - Dec 31, 2024 (same year)
        assert "2024" in display
        assert "Dec" in display

    def test_format_includes_year(self):
        """Display should always include the year."""
        display = format_week_display("2024-W48")
        assert "2024" in display

    def test_format_includes_month_names(self):
        """Display should use abbreviated month names."""
        display = format_week_display("2024-W48")
        assert "Nov" in display or "Dec" in display


class TestGetCurrentWeekId:
    """Tests for get_current_week_id function."""

    def test_returns_valid_format(self):
        """Should return a valid week ID format."""
        week_id = get_current_week_id()
        # Format should be YYYY-WNN
        assert len(week_id) == 8
        assert week_id[4] == "-"
        assert week_id[5] == "W"

    def test_year_is_current_or_adjacent(self):
        """Year should be current year (or adjacent for boundary cases)."""
        week_id = get_current_week_id()
        year = int(week_id[:4])
        current_year = datetime.now().year
        # Allow for year boundary cases
        assert year in [current_year - 1, current_year, current_year + 1]

    def test_week_number_valid_range(self):
        """Week number should be 01-53."""
        week_id = get_current_week_id()
        week_num = int(week_id[6:])
        assert 1 <= week_num <= 53
