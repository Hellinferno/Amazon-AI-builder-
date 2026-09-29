"""Money as integer paise.

External amounts are decimal strings such as "50000.00". They are converted to
integer minor units at validation and never pass through binary floats.
"""

import re

CURRENCY = "INR"
MINOR_UNITS_PER_MAJOR = 100

# ASCII digits only; at most two decimal places; no exponent, sign prefix "+",
# thousands separators, or surrounding whitespace.
_MONEY_RE = re.compile(r"(?P<sign>-?)(?P<major>[0-9]{1,13})(?:\.(?P<minor>[0-9]{1,2}))?")


class MoneyError(ValueError):
    """An external amount is not a valid decimal string."""


def parse_money(value: object, *, allow_negative: bool = False) -> int:
    """Convert a decimal string to integer paise.

    Negative amounts are rejected unless ``allow_negative`` is set, which is
    only intended for the opening balance.
    """
    if not isinstance(value, str):
        raise MoneyError("amount must be a decimal string, not a number")
    match = _MONEY_RE.fullmatch(value)
    if match is None:
        raise MoneyError(
            "amount must be digits with at most two decimal places, e.g. 50000.00"
        )
    if match["sign"] and not allow_negative:
        raise MoneyError("amount must not be negative")
    minor = (match["minor"] or "").ljust(2, "0")
    paise = int(match["major"]) * MINOR_UNITS_PER_MAJOR + int(minor)
    return -paise if match["sign"] else paise


def format_money(paise: int) -> str:
    """Render integer paise as a decimal string with exactly two decimals."""
    if isinstance(paise, bool) or not isinstance(paise, int):
        raise MoneyError("paise must be an integer")
    major, minor = divmod(abs(paise), MINOR_UNITS_PER_MAJOR)
    sign = "-" if paise < 0 else ""
    return f"{sign}{major}.{minor:02d}"
