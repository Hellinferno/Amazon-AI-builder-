from datetime import date

import pytest

from cashflow.dates import MAX_HORIZON_DAYS, DateError, parse_date, validate_horizon

AS_OF = date(2026, 10, 5)


def test_parse_valid_date():
    assert parse_date("2026-10-05") == AS_OF
    assert parse_date("2028-02-29") == date(2028, 2, 29)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "2026-02-30",
        "2026-13-01",
        "2027-02-29",
        "05-10-2026",
        "2026/10/05",
        "20261005",
        "2026-10-5",
        "2026-10-05T00:00:00",
        " 2026-10-05",
        "2026-W41-1",
        "next Friday",
    ],
)
def test_parse_rejects_malformed_dates(text):
    with pytest.raises(DateError):
        parse_date(text)


@pytest.mark.parametrize("value", [None, 20261005, AS_OF])
def test_parse_rejects_non_strings(value):
    with pytest.raises(DateError):
        parse_date(value)


def test_horizon_may_equal_as_of():
    validate_horizon(AS_OF, AS_OF)


def test_horizon_must_not_precede_as_of():
    with pytest.raises(DateError, match="precede"):
        validate_horizon(AS_OF, date(2026, 10, 4))


def test_horizon_cap_is_inclusive():
    validate_horizon(AS_OF, date(2027, 1, 3))  # exactly 90 days
    assert (date(2027, 1, 3) - AS_OF).days == MAX_HORIZON_DAYS
    with pytest.raises(DateError, match="90"):
        validate_horizon(AS_OF, date(2027, 1, 4))
