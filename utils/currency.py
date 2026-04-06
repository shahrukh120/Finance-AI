"""
Currency conversion utilities.

Rates are approximate USD-based exchange rates.
In production, swap `get_rate()` for a live API (e.g. exchangerate-api.com).
"""

# {code: (name, symbol, rate_to_usd)}
# rate_to_usd = how many USD you get for 1 unit of this currency
CURRENCIES = {
    "USD": ("US Dollar", "$", 1.0),
    "EUR": ("Euro", "\u20ac", 1.08),
    "GBP": ("British Pound", "\u00a3", 1.27),
    "JPY": ("Japanese Yen", "\u00a5", 0.0067),
    "CAD": ("Canadian Dollar", "CA$", 0.74),
    "AUD": ("Australian Dollar", "A$", 0.65),
    "CHF": ("Swiss Franc", "CHF", 1.13),
    "CNY": ("Chinese Yuan", "\u00a5", 0.14),
    "INR": ("Indian Rupee", "\u20b9", 0.012),
    "PKR": ("Pakistani Rupee", "\u20a8", 0.0036),
    "BDT": ("Bangladeshi Taka", "\u09f3", 0.0091),
    "LKR": ("Sri Lankan Rupee", "Rs", 0.0031),
    "NPR": ("Nepalese Rupee", "Rs", 0.0075),
    "MXN": ("Mexican Peso", "MX$", 0.058),
    "BRL": ("Brazilian Real", "R$", 0.20),
    "ARS": ("Argentine Peso", "AR$", 0.0011),
    "COP": ("Colombian Peso", "COL$", 0.00024),
    "CLP": ("Chilean Peso", "CL$", 0.0011),
    "KRW": ("South Korean Won", "\u20a9", 0.00074),
    "SGD": ("Singapore Dollar", "S$", 0.74),
    "HKD": ("Hong Kong Dollar", "HK$", 0.13),
    "TWD": ("Taiwan Dollar", "NT$", 0.031),
    "THB": ("Thai Baht", "\u0e3f", 0.029),
    "MYR": ("Malaysian Ringgit", "RM", 0.22),
    "PHP": ("Philippine Peso", "\u20b1", 0.018),
    "IDR": ("Indonesian Rupiah", "Rp", 0.000063),
    "VND": ("Vietnamese Dong", "\u20ab", 0.000041),
    "AED": ("UAE Dirham", "AED", 0.27),
    "SAR": ("Saudi Riyal", "SAR", 0.27),
    "QAR": ("Qatari Riyal", "QAR", 0.27),
    "KWD": ("Kuwaiti Dinar", "KWD", 3.25),
    "BHD": ("Bahraini Dinar", "BHD", 2.65),
    "OMR": ("Omani Rial", "OMR", 2.60),
    "EGP": ("Egyptian Pound", "E\u00a3", 0.021),
    "ZAR": ("South African Rand", "R", 0.055),
    "NGN": ("Nigerian Naira", "\u20a6", 0.00065),
    "KES": ("Kenyan Shilling", "KSh", 0.0077),
    "GHS": ("Ghanaian Cedi", "GH\u20b5", 0.069),
    "TRY": ("Turkish Lira", "\u20ba", 0.031),
    "RUB": ("Russian Ruble", "\u20bd", 0.011),
    "PLN": ("Polish Zloty", "z\u0142", 0.25),
    "SEK": ("Swedish Krona", "kr", 0.096),
    "NOK": ("Norwegian Krone", "kr", 0.093),
    "DKK": ("Danish Krone", "kr", 0.15),
    "CZK": ("Czech Koruna", "K\u010d", 0.044),
    "HUF": ("Hungarian Forint", "Ft", 0.0027),
    "RON": ("Romanian Leu", "lei", 0.22),
    "ILS": ("Israeli Shekel", "\u20aa", 0.28),
    "NZD": ("New Zealand Dollar", "NZ$", 0.60),
}


def get_rate(from_currency: str, to_currency: str = "USD") -> float:
    """
    Return the conversion rate from `from_currency` to `to_currency`.
    Both must be keys in CURRENCIES.
    """
    if from_currency == to_currency:
        return 1.0
    from_to_usd = CURRENCIES[from_currency][2]
    to_to_usd = CURRENCIES[to_currency][2]
    return from_to_usd / to_to_usd


def convert(amount: float, from_currency: str, to_currency: str = "USD") -> float:
    """Convert an amount between currencies. Returns rounded to 2 decimals."""
    return round(amount * get_rate(from_currency, to_currency), 2)


def get_symbol(code: str) -> str:
    """Return the currency symbol for a code."""
    return CURRENCIES.get(code, ("", code, 1.0))[1]


def currency_choices() -> list[dict]:
    """
    Return a sorted list of dicts for template dropdowns.
    [{"code": "USD", "name": "US Dollar", "symbol": "$"}, ...]
    """
    choices = []
    for code, (name, symbol, _) in CURRENCIES.items():
        choices.append({"code": code, "name": name, "symbol": symbol})
    # USD first, then alphabetical by name
    choices.sort(key=lambda c: (c["code"] != "USD", c["name"]))
    return choices
