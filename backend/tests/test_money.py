import pytest

from cashflow.money import MoneyError, format_money, parse_money


@pytest.mark.parametrize(
    ("text", "paise"),
    [
        ("0", 0),
        ("0.00", 0),
        ("50000.00", 5_000_000),
        ("50000", 5_000_000),
        ("0.1", 10),
        ("0.01", 1),
        ("19.99", 1999),
        ("9999999999999.99", 999_999_999_999_999),
    ],
)
def test_parse_valid_amounts(text, paise):
    assert parse_money(text) == paise


@pytest.mark.parametrize(
    "text",
    [
        "",
        " 10.00",
        "10.00 ",
        "10.001",
        "10.",
        ".50",
        "+10.00",
        "1,000.00",
        "1e3",
        "NaN",
        "Infinity",
        "-inf",
        "abc",
        "१०.००",
        "=1+1",
        "12345678901234.00",
    ],
)
def test_parse_rejects_malformed_amounts(text):
    with pytest.raises(MoneyError):
        parse_money(text, allow_negative=True)


@pytest.mark.parametrize("value", [10.0, 10, None, True, b"10.00"])
def test_parse_rejects_non_strings(value):
    with pytest.raises(MoneyError):
        parse_money(value)


def test_negative_rejected_by_default():
    with pytest.raises(MoneyError, match="negative"):
        parse_money("-15000.00")


def test_negative_allowed_for_opening_balance():
    assert parse_money("-15000.00", allow_negative=True) == -1_500_000


@pytest.mark.parametrize(
    ("paise", "text"),
    [(0, "0.00"), (1, "0.01"), (5_000_000, "50000.00"), (-1_500_000, "-15000.00"), (-5, "-0.05")],
)
def test_format(paise, text):
    assert format_money(paise) == text


@pytest.mark.parametrize("value", [1.0, "100", None, True])
def test_format_rejects_non_integers(value):
    with pytest.raises(MoneyError):
        format_money(value)


def test_round_trip_has_no_float_drift():
    # 0.10 + 0.20 is the classic binary-float failure; paise stay exact.
    assert parse_money("0.10") + parse_money("0.20") == parse_money("0.30")
    for text in ("0.07", "1.15", "33333.33", "-99999.99"):
        assert format_money(parse_money(text, allow_negative=True)) == text
