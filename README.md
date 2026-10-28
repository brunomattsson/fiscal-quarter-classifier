# fiscal-quarter-classifier

Maps a date to its fiscal quarter and week, given a configurable fiscal-year start month and a year-numbering scheme. Standard library only, no third-party dependencies.

## Install / run

Add `src/` to your `PYTHONPATH` and import:

```python
from fiscal_quarter_classifier import FiscalCalendar, FiscalPeriod
from datetime import date

cal = FiscalCalendar(fiscal_start_month=4, year_numbering="starts_in")
period: FiscalPeriod = cal.classify(date(2024, 6, 15))
print(period.fiscal_year, period.quarter, period.week_of_quarter, period.week_of_year)
# 2024 2 7 20
```

`FiscalCalendar(fiscal_start_month, year_numbering="starts_in", week_starts_on="monday", clock=date.today)` → `.classify(date)` returns a `FiscalPeriod` with `.fiscal_year`, `.quarter`, `.week_of_quarter`, `.week_of_year`.

## Why

Every organisation that reports on a non-calendar fiscal year ends up re-implementing the same date arithmetic, usually badly. The goal here is one small, dependency-free classifier that handles the common shapes (calendar-aligned start month, Monday/Sunday/Saturday week starts, starts-in vs ends-in year labelling) without dragging in a date library ten times its size.

The deliberate trade-off: weeks are pure 7-day buckets counted from the fiscal-year boundary, **not** ISO-8601 partial weeks. Week 1 always contains the fiscal new year. This is simpler to reason about and matches how most enterprise reporting tools lay out "fiscal week 1", but it means week boundaries will not line up with ISO week numbers — pick one model and commit.

## Edge cases worth knowing

- **Quarter lengths.** Quarters 1–3 are 91 days (13 weeks). Quarter 4 absorbs the 365th day (and 366th in leap years) as a 14th week, so a leap-year Q4 has 14 weeks rather than 13.
- **Year numbering.** `starts_in` labels the fiscal year by the calendar year it begins in (Apr 2024 → FY 2024). `ends_in` labels it by the calendar year it ends in (Apr 2024 → Mar 2025 → FY 2025). Mixing the two across systems is the most common source of "why are these numbers one off" bugs — pick one per integration.
- **December start.** A fiscal year starting in December spans a calendar-year boundary; dates in January still belong to the fiscal year that started the previous December.
