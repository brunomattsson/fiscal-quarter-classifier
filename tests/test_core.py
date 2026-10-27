"""Tests for fiscal_quarter_classifier.core."""

import datetime as dt
import unittest

from fiscal_quarter_classifier.core import FiscalCalendar, FiscalPeriod


class TestFiscalCalendarConstruction(unittest.TestCase):
    def test_default_calendar_january_starts_in_monday(self):
        cal = FiscalCalendar(fiscal_start_month=1)
        self.assertEqual(cal.fiscal_start_month, 1)
        self.assertEqual(cal.year_numbering, "starts_in")
        self.assertEqual(cal.week_starts_on, "monday")

    def test_invalid_month_raises(self):
        with self.assertRaises(ValueError):
            FiscalCalendar(fiscal_start_month=0)
        with self.assertRaises(ValueError):
            FiscalCalendar(fiscal_start_month=13)

    def test_invalid_year_numbering_raises(self):
        with self.assertRaises(ValueError):
            FiscalCalendar(fiscal_start_month=1, year_numbering="calvinball")

    def test_invalid_week_starts_on_raises(self):
        with self.assertRaises(ValueError):
            FiscalCalendar(fiscal_start_month=1, week_starts_on="tuesday")


class TestJanuaryCalendar(unittest.TestCase):
    """A January-start calendar coincides with the calendar year under
    'starts_in' numbering, which makes assertions easy to verify by hand."""

    def setUp(self):
        self.cal = FiscalCalendar(fiscal_start_month=1, year_numbering="starts_in")

    def test_jan_1_is_q1_w1(self):
        p = self.cal.classify(dt.date(2024, 1, 1))
        self.assertEqual(p.fiscal_year, 2024)
        self.assertEqual(p.quarter, 1)
        self.assertEqual(p.week_of_quarter, 1)
        self.assertEqual(p.week_of_year, 1)

    def test_day_91_is_q2_w1(self):
        # 2024-04-01 is day index 91 (0-based) → first day of Q2
        p = self.cal.classify(dt.date(2024, 4, 1))
        self.assertEqual(p.quarter, 2)
        self.assertEqual(p.week_of_quarter, 1)
        self.assertEqual(p.week_of_year, 14)

    def test_day_182_is_q3_w1(self):
        # 2024-07-01 is day index 182 (0-based) → first day of Q3
        p = self.cal.classify(dt.date(2024, 7, 1))
        self.assertEqual(p.quarter, 3)
        self.assertEqual(p.week_of_quarter, 1)
        self.assertEqual(p.week_of_year, 27)

    def test_day_273_is_q4_w1(self):
        p = self.cal.classify(dt.date(2024, 9, 30))
        self.assertEqual(p.quarter, 4)
        self.assertEqual(p.week_of_quarter, 1)
        self.assertEqual(p.week_of_year, 40)

    def test_dec_31_2024_is_q4_w14_leap(self):
        # 2024 is a leap year: 366 days, so Dec 31 lands in week 14 of Q4.
        p = self.cal.classify(dt.date(2024, 12, 31))
        self.assertEqual(p.quarter, 4)
        self.assertEqual(p.week_of_quarter, 14)
        self.assertEqual(p.fiscal_year, 2024)

    def test_dec_31_2023_is_q4_w13_non_leap(self):
        # 2023 has 365 days: index 364 → week (364//7)+1 = 53, q4 week 14.
        p = self.cal.classify(dt.date(2023, 12, 31))
        self.assertEqual(p.quarter, 4)
        self.assertEqual(p.week_of_quarter, 14)


class TestAprilStartCalendar(unittest.TestCase):
    def setUp(self):
        self.cal = FiscalCalendar(
            fiscal_start_month=4, year_numbering="starts_in"
        )

    def test_april_1_is_q1_w1(self):
        p = self.cal.classify(dt.date(2024, 4, 1))
        self.assertEqual(p.fiscal_year, 2024)
        self.assertEqual(p.quarter, 1)
        self.assertEqual(p.week_of_year, 1)

    def test_march_31_belongs_to_previous_fy(self):
        p = self.cal.classify(dt.date(2024, 3, 31))
        self.assertEqual(p.fiscal_year, 2023)
        self.assertEqual(p.quarter, 4)

    def test_july_1_is_q2(self):
        # FY2024 started Apr 1 2024. Jul 1 is day 91 → Q2 W1.
        p = self.cal.classify(dt.date(2024, 7, 1))
        self.assertEqual(p.quarter, 2)
        self.assertEqual(p.week_of_quarter, 1)


class TestYearNumbering(unittest.TestCase):
    def test_ends_in_label(self):
        cal = FiscalCalendar(
            fiscal_start_month=4, year_numbering="ends_in"
        )
        # FY starting Apr 2024 ends Mar 2025 → labelled 2025.
        p = cal.classify(dt.date(2024, 4, 1))
        self.assertEqual(p.fiscal_year, 2025)

    def test_starts_in_label(self):
        cal = FiscalCalendar(
            fiscal_start_month=4, year_numbering="starts_in"
        )
        p = cal.classify(dt.date(2024, 4, 1))
        self.assertEqual(p.fiscal_year, 2024)


class TestDecemberStartCrossesCalendarYear(unittest.TestCase):
    """December start with 'starts_in' numbering: Dec 2023 is FY2023,
    Jan 2024 still FY2023."""

    def setUp(self):
        self.cal = FiscalCalendar(
            fiscal_start_month=12, year_numbering="starts_in"
        )

    def test_dec_1_2023_is_new_fy(self):
        p = self.cal.classify(dt.date(2023, 12, 1))
        self.assertEqual(p.fiscal_year, 2023)
        self.assertEqual(p.quarter, 1)
        self.assertEqual(p.week_of_year, 1)

    def test_jan_15_2024_still_fy2023(self):
        p = self.cal.classify(dt.date(2024, 1, 15))
        self.assertEqual(p.fiscal_year, 2023)


class TestClockInjection(unittest.TestCase):
    def test_today_uses_injected_clock(self):
        fixed = dt.date(2024, 6, 15)
        cal = FiscalCalendar(
            fiscal_start_month=1, year_numbering="starts_in", clock=lambda: fixed
        )
        p = cal.today()
        self.assertEqual(p.fiscal_year, 2024)
        self.assertEqual(p.quarter, 2)


class TestFiscalPeriodFields(unittest.TestCase):
    def test_all_fields_present(self):
        cal = FiscalCalendar(fiscal_start_month=1)
        p = cal.classify(dt.date(2024, 1, 1))
        self.assertIsInstance(p, FiscalPeriod)
        self.assertEqual(
            set(p.__dict__),
            {"fiscal_year", "quarter", "week_of_quarter", "week_of_year"},
        )


if __name__ == "__main__":
    unittest.main()
