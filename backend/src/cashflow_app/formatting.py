"""Display helpers shared by prose composers and the reminder template."""

from datetime import date


def money(value: str | None, currency: str = "INR") -> str:
    """Render a two-decimal money string with thousands separators: INR 40,000.00.

    The digits are never changed, so the grounding check can match the value
    back to the tool result after removing the separators.
    """
    if value is None:
        return "n/a"
    sign = "-" if value.startswith("-") else ""
    digits = value.lstrip("-")
    whole, _, frac = digits.partition(".")
    return f"{currency} {sign}{int(whole):,}.{frac or '00'}"


def display_date(value: str | date | None) -> str:
    if not value:
        return "n/a"
    d = value if isinstance(value, date) else date.fromisoformat(value)
    return f"{d.day} {d.strftime('%B %Y')}"
