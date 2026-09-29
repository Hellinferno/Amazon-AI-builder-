"""Business dates.

Dates are ISO calendar dates in the business timezone. Nothing here reads the
system clock: every calculation derives from an explicit as-of date.
"""

import re
from datetime import date

BUSINESS_TIMEZONE = "Asia/Kolkata"
MAX_HORIZON_DAYS = 90

_ISO_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class DateError(ValueError):
    """A date is malformed or violates a period rule."""


def parse_date(value: object) -> date:
    """Parse a strict ``YYYY-MM-DD`` calendar date."""
    if not isinstance(value, str):
        raise DateError("date must be a string in YYYY-MM-DD format")
    if _ISO_DATE_RE.fullmatch(value) is None:
        raise DateError("date must be in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise DateError("date is not a real calendar date") from None


def validate_horizon(as_of_date: date, horizon_end: date) -> None:
    """Check the inclusive forecast interval ``[as_of_date, horizon_end]``."""
    if horizon_end < as_of_date:
        raise DateError("horizon end must not precede the as-of date")
    if (horizon_end - as_of_date).days > MAX_HORIZON_DAYS:
        raise DateError(
            f"horizon end must be within {MAX_HORIZON_DAYS} days of the as-of date"
        )
