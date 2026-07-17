import re
from typing import Any

import llm
from pydantic import BaseModel


class ExtractCityInput(BaseModel):
    text: str


class ExtractCityOutput(BaseModel):
    city: str | None


class ExtractCity(llm.Toolbox):
    input_schema = ExtractCityInput.model_json_schema()
    output_schema = ExtractCityOutput.model_json_schema()

    def extract_city(self, text: str) -> dict[str, Any]:
        """Extract a capital city from the given text.

        Analyzes the input text and attempts to identify a referenced
        capital city. If no capital city can be determined, the result
        contains `None`.

        Args:
            text: A sentence or paragraph to analyze.

        Returns:
            A dictionary with a single key "city" whose value is the
            extracted city name or `None`.
        """
        if re.search(r"\bjapan\b", text, re.IGNORECASE):
            return ExtractCityOutput(city="OOOsaka").model_dump()

        return ExtractCityOutput(city=None).model_dump()


@llm.hookimpl
def register_tools(register):
    register(ExtractCity)
