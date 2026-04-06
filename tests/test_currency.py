"""
Tests for multi-currency support.
Run with: python -m pytest tests/test_currency.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.currency import convert, get_rate, get_symbol, currency_choices, CURRENCIES


class TestConvert:
    def test_usd_to_usd(self):
        assert convert(100.0, "USD", "USD") == 100.0

    def test_inr_to_usd(self):
        result = convert(1000.0, "INR", "USD")
        assert result == round(1000.0 * 0.012, 2)

    def test_eur_to_usd(self):
        result = convert(100.0, "EUR", "USD")
        assert result == round(100.0 * 1.08, 2)

    def test_gbp_to_usd(self):
        result = convert(50.0, "GBP", "USD")
        assert result == round(50.0 * 1.27, 2)

    def test_pkr_to_usd(self):
        result = convert(50000.0, "PKR", "USD")
        assert result == round(50000.0 * 0.0036, 2)

    def test_jpy_to_usd(self):
        result = convert(10000.0, "JPY", "USD")
        assert result == round(10000.0 * 0.0067, 2)


class TestGetRate:
    def test_same_currency(self):
        assert get_rate("USD", "USD") == 1.0
        assert get_rate("EUR", "EUR") == 1.0

    def test_usd_to_other(self):
        rate = get_rate("USD", "EUR")
        # 1 USD = (1.0 / 1.08) EUR
        assert round(rate, 4) == round(1.0 / 1.08, 4)

    def test_cross_rate(self):
        # GBP -> INR via USD
        rate = get_rate("GBP", "INR")
        expected = 1.27 / 0.012
        assert round(rate, 2) == round(expected, 2)


class TestGetSymbol:
    def test_known_currencies(self):
        assert get_symbol("USD") == "$"
        assert get_symbol("EUR") == "\u20ac"
        assert get_symbol("GBP") == "\u00a3"
        assert get_symbol("INR") == "\u20b9"

    def test_unknown_currency(self):
        assert get_symbol("XYZ") == "XYZ"


class TestCurrencyChoices:
    def test_returns_list(self):
        choices = currency_choices()
        assert isinstance(choices, list)
        assert len(choices) == len(CURRENCIES)

    def test_usd_first(self):
        choices = currency_choices()
        assert choices[0]["code"] == "USD"

    def test_has_required_fields(self):
        choices = currency_choices()
        for c in choices:
            assert "code" in c
            assert "name" in c
            assert "symbol" in c

    def test_all_currencies_present(self):
        choices = currency_choices()
        codes = {c["code"] for c in choices}
        for code in CURRENCIES:
            assert code in codes
