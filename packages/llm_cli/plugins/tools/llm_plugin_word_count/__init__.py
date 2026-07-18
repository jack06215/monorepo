from typing import Any

import llm
from pydantic import BaseModel


class WordCountInput(BaseModel):
    text: str


class WordCountOutput(BaseModel):
    characters: int
    words: int
    lines: int


class WordCount(llm.Toolbox):
    input_schema = WordCountInput.model_json_schema()
    output_schema = WordCountOutput.model_json_schema()

    def count(self, text: str) -> dict[str, Any]:
        """Count characters, words, and lines in the given text.

        Args:
            text: The text to analyze.

        Returns:
            A dictionary containing counts for characters, words, and lines.
        """
        return WordCountOutput(
            characters=len(text),
            words=len(text.split()),
            lines=text.count("\n") + 1 if text else 0,
        ).model_dump()


@llm.hookimpl
def register_tools(register):
    register(WordCount)
