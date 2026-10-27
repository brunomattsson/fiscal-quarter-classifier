"""Core fiscal calendar logic."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Callable, Tuple


WeekNumbering = str
_DATE = _dt.date
# A clock function returns the current date. Accepting it as a callable
# (rather than reading datetime.date.today() internally) keeps every
# operation deterministic and testable without monkeypatching.
Clock = Callable[[], _DATE]


def _today() -> _DATE:
    return _dt.date.today()


@dataclass(frozen=True)
class FiscalPeriod:
    """The fiscal classification of a single date.

    Attributes
    ----------
    fiscal_year : int
        The fiscal-year label. Under "starts_in" numbering the year is the
        *calendar* year in which the fiscal year begins (a fiscal year starting
        April 2024 is labelled 2024). Under "ends_in" numbering the year is
        the calendar year in which the fiscal year ends (a fiscal year ending
        March 2025 is labelled 2025).
    quarter : int
        1–4.
    week_of_quarter : int
        1-based week within the quarter (1–13 when the quarter is exactly 91
        days; 1–14 in a 14th-week quarter).
    week_of_year : int
        1-based week within the fiscal year.
    """

    fiscal_year: int
    quarter: int
    week_of_quarter: int
    week_of_year: int


@dataclass(frozen=True)
class FiscalCalendar:
    """A configurable fiscal calendar.

    Parameters
    ----------
    fiscal_start_month : int
        Month (1–12) in which the fiscal year starts.
    year_numbering : str
        Either "starts_in" or "ends_in". See :class:`FiscalPeriod` for the
        difference. Picking one scheme (rather than supporting arbitrary
        label offsets) avoids the kind of off-by-one ambiguity that makes
        multi-vendor fiscal data hard to reconcile.
    week_starts_on : str
        One of "monday", "sunday", "saturday". Determines the first day of
        each fiscal week.
    clock : Callable[[], datetime.date], optional
        Function returning "today". Override in tests; defaults to
        :func:`datetime.date.today`.

    Notes
    -----
    Weeks are pure 7-day buckets counted from the fiscal-year boundary, not
    ISO-8601 partial weeks. Week 1 always contains the fiscal new year, even
    if that new year does not fall on ``week_starts_on``. A year is 52 weeks
    (364 days); the 365th/366th day rolls into a 53rd partial week so no date
    is ever unclassifiable.
    """

    fiscal_start_month: int
    year_numbering: WeekNumbering = "starts_in"
    week_starts_on: str = "monday"
    clock: Clock = _today

    _WEEKDAY_MAP = {
        "monday": 0,
        "sunday": 6,
        "saturday": 5,
    }

    def __post_init__(self) -> None:
        if not 1 <= self.fiscal_start_month <= 12:
            raise ValueError(
                f"fiscal_start_month must be 1–12, got {self.fiscal_start_month}"
            )
        if self.year_numbering not in ("starts_in", "ends_in"):
            raise ValueError(
                f"year_numbering must be 'starts_in' or 'ends_in', "
                f"got {self.year_numbering!r}"
            )
        if self.week_starts_on not in self._WEEKDAY_MAP:
            raise ValueError(
                "week_starts_on must be one of "
                f"{sorted(self._WEEKDAY_MAP)!r}, got {self.week_starts_on!r}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def classify(self, date: _DATE) -> FiscalPeriod:
        """Classify ``date`` into a fiscal quarter and week."""
        fy_start = self._fy_start_for(date)
        if date < fy_start:
            fy_start = self._fy_start_for(date, prev=True)

        days_into_year = (date - fy_start).days
        week_of_year = days_into_year // 7 + 1
        quarter, week_of_quarter = self._quarter_and_week(days_into_year)
        fiscal_year = self._label_for(fy_start)

        return FiscalPeriod(
            fiscal_year=fiscal_year,
            quarter=quarter,
            week_of_quarter=week_of_quarter,
            week_of_year=week_of_year,
        )

    def today(self) -> FiscalPeriod:
        """Classify the date returned by :attr:`clock`."""
        return self.classify(self.clock())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _fy_start_for(self, date: _DATE, prev: bool = False) -> _DATE:
        """Return the fiscal-year start date relevant to ``date``.

        With ``prev=True`` the immediately preceding fiscal-year start is
        returned (used when ``date`` falls before the current year's start).
        """
        year = date.year - (1 if prev else 0)
        candidate = _dt.date(year, self.fiscal_start_month, 1)
        if prev and candidate > date:
            # e.g. fiscal_start_month is later in the year than ``date``
            candidate = _dt.date(year - 1, self.fiscal_start_month, 1)
        return candidate

    def _label_for(self, fy_start: _DATE) -> int:
        if self.year_numbering == "starts_in":
            return fy_start.year
        # "ends_in": label is the calendar year in which the fiscal year ends.
        return fy_start.year + 1

    @staticmethod
    def _quarter_and_week(days_into_year: int) -> Tuple[int, int]:
        """Map an offset-in-year to (quarter, week_of_quarter).

        Quarters 1–3 are fixed at 91 days (13 weeks); quarter 4 absorbs the
        365th and (in leap years) 366th day as a 14th week, so the model stays
        simple while still covering every calendar date.
        """
        if days_into_year < 91:
            return 1, days_into_year // 7 + 1
        if days_into_year < 182:
            return 2, (days_into_year - 91) // 7 + 1
        if days_into_year < 273:
            return 3, (days_into_year - 182) // 7 + 1
        return 4, (days_into_year - 273) // 7 + 1
