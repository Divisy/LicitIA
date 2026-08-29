"""Tests for presupuesto parsing."""
from app.services.tender_summary.presupuesto_extraction import _parse_number


def test_parse_number_colombian_thousands_with_dots():
    assert _parse_number("400.000.000") == 400_000_000.0
    assert _parse_number("1.234.567.890") == 1_234_567_890.0
    assert _parse_number("312.026") == 312_026.0


def test_parse_number_us_thousands_with_commas():
    assert _parse_number("400,000,000") == 400_000_000.0


def test_parse_number_colombian_decimal_comma():
    assert _parse_number("400.000.000,00") == 400_000_000.0


def test_parse_number_keeps_small_decimals():
    assert _parse_number("24.5") == 24.5
    assert _parse_number("12.5") == 12.5
