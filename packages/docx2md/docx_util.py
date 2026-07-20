"""Utility functions for parsing docx files."""

# mypy: disable-error-code="union-attr"

import docx
import docx.enum.dml
import docx.styles
import docx.table
import docx.text
import docx.text.font
import docx.text.paragraph

from packages.docx2md import types


def is_strong(font: docx.text.font.Font) -> bool:
    """Check if font is bold."""
    if font.bold or (
        font.color.type == docx.enum.dml.MSO_COLOR_TYPE.THEME
        and (
            font.color.theme_color == docx.enum.dml.MSO_THEME_COLOR.DARK_1
            or font.color.theme_color == docx.enum.dml.MSO_THEME_COLOR.DARK_2
        )
    ):
        return True
    return False


def is_accent(font: docx.text.font.Font) -> bool:
    """Check if font is accent."""
    if font.underline or (
        font.color.type == docx.enum.dml.MSO_COLOR_TYPE.THEME
        and (
            font.color.theme_color == docx.enum.dml.MSO_THEME_COLOR.ACCENT_1
            or font.color.theme_color == docx.enum.dml.MSO_THEME_COLOR.ACCENT_2
            or font.color.theme_color == docx.enum.dml.MSO_THEME_COLOR.ACCENT_3
            or font.color.theme_color == docx.enum.dml.MSO_THEME_COLOR.ACCENT_4
            or font.color.theme_color == docx.enum.dml.MSO_THEME_COLOR.ACCENT_5
            or font.color.theme_color == docx.enum.dml.MSO_THEME_COLOR.ACCENT_6
        )
    ):
        return True
    return False


def get_text_runs(para: docx.text.paragraph.Paragraph) -> list[types.TextRun]:
    """Parse paragraph into style-aware text block."""
    runs = []
    for run in para.runs:
        result = types.TextRun(text=run.text, style=types.TextStyle())
        if result.text == "":
            continue
        try:
            if run.style == docx.enum.style.WD_BUILTIN_STYLE.HYPERLINK:
                result.style.hyperlink = run.text
        except Exception:
            result.style.hyperlink = "error:ppt-link-parsing-issue"
        if is_accent(run.font):
            result.style.is_accent = True
        if is_strong(run.font):
            result.style.is_strong = True
        if run.font.color.type == docx.enum.dml.MSO_COLOR_TYPE.RGB:
            result.style.color_rgb = run.font.color.rgb
        runs.append(result)
    return runs


def is_title(para: docx.text.paragraph.Paragraph) -> bool:
    """Check if a paragraph is a title."""
    if para.style is not None and (
        para.style.name
        in [
            "Heading 1",
            "Heading 2",
            "Heading 3",
            "Heading 4",
            "Heading 5",
            "Heading 6",
        ]
    ):
        return True
    return False


def is_list_block(para: docx.text.paragraph.Paragraph) -> bool:
    """Check if the paragraph is part of a list block."""
    # Get the numbering style of the paragraph (if any)
    if para._p.pPr is not None and para._p.pPr.numPr is not None:
        return True
    return False


def get_list_level(para: docx.text.paragraph.Paragraph) -> int:
    """Get the level of the list item (0-based level).

    See https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.numberinglevelreference?view=openxml-3.0.1#remarks.
    """
    if is_list_block(para):
        ilvl = para._p.pPr.numPr.ilvl
        if ilvl is not None:
            return int(ilvl.val)
    return -1
