from abc import ABC, abstractmethod
from re import Pattern


class CountryRegex(ABC):
    country_code: str

    @abstractmethod
    def patterns(self) -> dict[str, Pattern[str]]:
        """Return compiled regex patterns"""
