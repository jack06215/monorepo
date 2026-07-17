"""Types for docx to markdown conversion."""

from typing import Literal

import pydantic


class ConversionConfig(pydantic.BaseModel):
    """Configuration for PowerPoint to Markdown conversion."""

    disable_image: bool = False
    """Disable image extraction"""

    disable_escaping: bool = False
    """Do not attempt to escape special characters"""

    min_block_size: int = 0
    """The minimum character number of a text block to be converted"""


ElementType = Literal[
    "base_type",
    "title",
    "list_item",
    "paragraph",
    "image",
    "table",
]

ParagraphType = Literal["image", "text_runs"]

SlideType = Literal["general"]


class TextStyle(pydantic.BaseModel):
    """Text style."""

    is_accent: bool | None = False
    is_strong: bool | None = False
    color_rgb: tuple[int, int, int] | None = None
    hyperlink: str | None = None


class TextRun(pydantic.BaseModel):
    """A block of text."""

    text: str
    style: TextStyle


class Position(pydantic.BaseModel):
    """Position."""

    left: float
    top: float
    width: float
    height: float


class BaseElement(pydantic.BaseModel):
    """Shared element type."""

    type: ElementType = "base_type"
    position: Position | None = None
    style: TextStyle | None = None


class TitleElement(BaseElement):
    """Title element."""

    type: ElementType = "title"
    content: str
    level: int


class ListItemElement(BaseElement):
    """List item element."""

    type: ElementType = "list_item"
    content: list[TextRun]
    level: int = 1


class Image(pydantic.BaseModel):
    """Image element."""

    type: ParagraphType = "image"
    data: str
    alt_text: str = ""  # For accessibility


class ListOfTextRun(pydantic.BaseModel):
    """List of text runs."""

    type: ParagraphType = "text_runs"
    data: list[TextRun]


SupportedParagraphElement = Image | ListOfTextRun


class ParagraphElement(BaseElement):
    """Paragraph element."""

    type: ElementType = "paragraph"
    content: SupportedParagraphElement


class TableElement(BaseElement):
    """Table element."""

    type: ElementType = "table"
    content: list[list[list[TextRun]]]  # rows -> cols -> rich text


DocumentElement = TitleElement | ListItemElement | ParagraphElement | TableElement
"""Supported slide element type."""


Document = DocumentElement


class ParsedDocument(pydantic.BaseModel):
    """Parsed document."""

    body: list[Document]
