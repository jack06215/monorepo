"""Types for PowerPoint to Markdown conversion."""

from typing import Literal

import pydantic


class ConversionConfig(pydantic.BaseModel):
    """Configuration for PowerPoint to Markdown conversion."""

    disable_image: bool = False
    """Disable image extraction"""

    disable_escaping: bool = False
    """Do not attempt to escape special characters"""

    disable_notes: bool = False
    """Do not add presenter notes"""

    enable_slides: bool = False
    """Delineate slides with `\n---\n`"""

    min_block_size: int = 0
    """The minimum character number of a text block to be converted"""

    keep_similar_titles: bool = False
    """Keep similar titles (allow for repeated slide titles - One or more - Add (cont.) to the title)"""  # noqa: E501


ElementType = Literal[
    "base_type",
    "title",
    "list_item",
    "paragraph",
    "image",
    "table",
]

SlideType = Literal["general"]


class TextStyle(pydantic.BaseModel):
    """Text style."""

    is_accent: bool = False
    is_strong: bool = False
    color_rgb: tuple[int, int, int] | None = None
    hyperlink: str | None = None


class TextRun(pydantic.BaseModel):
    """A block of text. https://learn.microsoft.com/en-us/office/vba/api/powerpoint.textrange.runs."""

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


class ParagraphElement(BaseElement):
    """Paragraph element."""

    type: ElementType = "paragraph"
    content: list[TextRun]


class ImageElement(BaseElement):
    """Image element."""

    type: ElementType = "image"
    content: str
    alt_text: str = ""  # For accessibility


class TableElement(BaseElement):
    """Table element."""

    type: ElementType = "table"
    content: list[list[list[TextRun]]]  # rows -> cols -> rich text


SlideElement = (
    TitleElement | ListItemElement | ParagraphElement | ImageElement | TableElement
)
"""Supported slide element type."""


class GeneralSlide(pydantic.BaseModel):
    """Single-column slide element."""

    type: SlideType = "general"
    elements: list[SlideElement]
    notes: list[str] = []


Slide = GeneralSlide
"""Slide type."""


class ParsedPresentation(pydantic.BaseModel):
    """Holds presentation slides."""

    slides: list[Slide]
