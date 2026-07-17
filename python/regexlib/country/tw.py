import re
from re import Pattern

from regexlib.base import CountryRegex


class TaiwanRegex(CountryRegex):
    country_code = "TW"

    def patterns(self) -> dict[str, Pattern[str]]:
        return {
            # Mobile phone: 09xx-xxx-xxx
            "phone": re.compile(r"\b09\d{2}-?\d{3}-?\d{3}\b"),
            # National ID: A123456789
            "national_id": re.compile(r"\b[A-Z][12]\d{8}\b"),
            # Postal code (3 or 5 digits)
            "postal_code": re.compile(r"\b\d{3}(\d{2})?\b"),
        }
