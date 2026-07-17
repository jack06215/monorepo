import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic_core import to_json

from common.langchain_invoke import invoke_llm
from common.llm_client import (
    get_langchain_client,
)
from meetingbar.model import MeetingBarDType

SUMMARIZATION_PROMPT = """
You are given JSON data that represents meeting information.

Your task is to convert it into Japanese meeting notes.

INPUT:
{meeting_information}

STRICT RULES:
- Output only the formatted result. No explanations, no headers, no code blocks.
- Follow the format exactly as shown below.
- Date format must be: YYYY年MM月DD日(曜)
- Time format must be: HH:MM ~ HH:MM (24-hour, half-width ~)
- If a field is missing, null, or empty, output 「なし」.
- Do not infer or add any information.
- Do not change line order, spacing, or symbols.

OUTPUT FORMAT (MUST MATCH EXACTLY):
* タイトル: <value>
* 開催日: <value>
* 開始終了時間: <value>
* 場所: <value>
* 会議URL: <value>
* メモ: <value>
"""


@dataclass
class Args:
    json_path: Path


@dataclass
class Notification:
    title: str
    subtitle: str
    sound: str
    url: str

    @classmethod
    def from_meetingbar_json(cls, file: Path) -> Self:
        print(file.as_posix())
        return cls(
            title="Title",
            subtitle="subtitle",
            sound="Glass",
            url="https://www.google.com",
        )


def summarize_meetingbar_event(data: MeetingBarDType) -> None:
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger(__name__)
    template = PromptTemplate.from_template(SUMMARIZATION_PROMPT)

    chat = get_langchain_client("azure")
    parser = StrOutputParser()

    # Input data for the prompt
    input_data = {
        "title": "Google Calendar processor.",
        "meeting_information": f"{to_json(data).decode()}",
    }

    config = RunnableConfig(tags=["sample", "translation"])

    # Call the LLM safely with retries
    try:
        response = invoke_llm(
            template=template,
            chat=chat,
            parser=parser,
            logger=logger,
            input=input_data,
            config=config,
        )
        print("\n=== LLM Response ===")
        print(response)
    except Exception as e:
        logger.error("Failed to invoke LLM: %s", e)
