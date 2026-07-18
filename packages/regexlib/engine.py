from collections.abc import Iterable
from re import Pattern

from regexlib.base import CountryRegex
from regexlib.country.intl import COMMON_PATTERNS


class RegexEngine:
    def __init__(self, countries: Iterable[CountryRegex]):
        self.patterns: dict[str, list[Pattern[str]]] = {}

        # Load common patterns
        for name, rx in COMMON_PATTERNS.items():
            self.patterns.setdefault(name, []).append(rx)

        # Load country-specific patterns
        for country in countries:
            for name, rx in country.patterns().items():
                key = f"{country.country_code.lower()}_{name}"
                self.patterns.setdefault(key, []).append(rx)

    def detect(self, text: str) -> dict[str, list[str]]:
        results: dict[str, list[str]] = {}

        for name, regex_list in self.patterns.items():
            matches: list[str] = []
            for rx in regex_list:
                matches.extend(m.group(0) for m in rx.finditer(text))
            if matches:
                results[name] = matches

        return results
