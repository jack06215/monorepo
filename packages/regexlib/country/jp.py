import re
from re import Pattern

from regexlib.base import CountryRegex


class JapanRegex(CountryRegex):
    country_code = "JP"

    def patterns(self) -> dict[str, Pattern[str]]:
        return {
            # Phone: 090-1234-5678 / 03-1234-5678
            "phone": re.compile(r"(?<!\d)0(?:\d{1,4})-(?:\d{1,4})-\d{4}(?!\d)"),
            # Postal code: 123-4567
            "postal_code": re.compile(r"(?<!\d)\d{3}-\d{4}(?!-\d)"),
            # My Number (12 digits)
            "my_number": re.compile(r"(?<!\d)\d{12}(?!\d)"),
        }
