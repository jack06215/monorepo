"""Office Word document parser."""

import base64
import functools
import operator
from typing import cast

import docx.document
import docx.drawing
import docx.table
import docx.text.font
import docx.text.hyperlink
import docx.text.paragraph
import docx.text.run

from docx2md import docx_util, types


class DocxElementProcessor:
    """Office Word document processor."""

    def __init__(self, config: types.ConversionConfig) -> None:
        """Constructor."""
        self.config = config

    def process_title(
        self,
        para: docx.text.paragraph.Paragraph,
    ) -> types.TitleElement:
        """Process a title."""
        if para.style is None:
            raise ValueError("Style is None")

        if para.style.name == "Heading 1":
            return types.TitleElement(
                content=para.text.strip(),
                level=1,
            )
        elif para.style.name == "Heading 2":
            return types.TitleElement(
                content=para.text.strip(),
                level=2,
            )
        elif para.style.name == "Heading 3":
            return types.TitleElement(
                content=para.text.strip(),
                level=3,
            )
        elif para.style.name == "Heading 4":
            return types.TitleElement(
                content=para.text.strip(),
                level=4,
            )
        elif para.style.name == "Heading 5":
            return types.TitleElement(
                content=para.text.strip(),
                level=5,
            )
        elif para.style.name == "Heading 6":
            return types.TitleElement(
                content=para.text.strip(),
                level=6,
            )
        else:
            raise ValueError("Style is not supported")

    def process_list_item(
        self,
        para: docx.text.paragraph.Paragraph,
    ) -> types.ListItemElement:
        """Process a list item."""
        return types.ListItemElement(
            content=docx_util.get_text_runs(para),
            level=docx_util.get_list_level(para),
        )

    def process_image(
        self,
        drawing: docx.drawing.Drawing,
    ) -> types.ParagraphElement:
        """Process a image."""
        # Namespace definition for document: http://officeopenxml.com/drwPic.php
        namespaces = {
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        }
        matched_xml = drawing._drawing.find(".//a:blip", namespaces=namespaces)
        image_id = cast(str, matched_xml.embed)
        image_byte = cast(
            bytes,
            drawing.part.related_parts[image_id]._blob,
        )

        image_64encoded = base64.b64encode(image_byte)
        # TODO[jack06215]: This is actually not true but it works for now.
        content_type = "image/png"
        image_str = f"data:{content_type};base64,{image_64encoded.decode()}"

        return types.ParagraphElement(
            content=types.Image(
                data=image_str,
                # TODO[jack06215]: We can try using GPT to generate alt text.
                alt_text="",
            )
        )

    def process_table(
        self,
        table: docx.table.Table,
    ) -> types.TableElement:
        """Process a table."""
        formatted_table: list[list[list[types.TextRun]]] = [
            [
                functools.reduce(
                    operator.iadd,
                    (docx_util.get_text_runs(p) for p in cell.paragraphs),
                    [],
                )
                for cell in row.cells
            ]
            for row in table.rows
        ]
        return types.TableElement(content=formatted_table)

    def process_hyperlink(
        self,
        link: docx.text.hyperlink.Hyperlink,
    ) -> types.ParagraphElement:
        """Process a hyperlink."""
        return types.ParagraphElement(
            content=types.ListOfTextRun(
                data=[
                    types.TextRun(
                        text=link.text,
                        style=types.TextStyle(hyperlink=link.address),
                    )
                ]
            )
        )

    def process_text_run(
        self,
        text: str,
        font: docx.text.font.Font | None,
    ) -> types.ParagraphElement | None:
        if text == "":
            return None

        strong = docx_util.is_strong(font) if font else False
        accent = docx_util.is_accent(font) if font else False

        return types.ParagraphElement(
            content=types.ListOfTextRun(
                data=[
                    types.TextRun(
                        text=text,
                        style=types.TextStyle(
                            is_strong=strong,
                            is_accent=accent,
                        ),
                    )
                ]
            )
        )


def parse(
    document: docx.document.Document,
    element_processor: DocxElementProcessor,
) -> types.ParsedDocument:
    """Parse an Office Word document."""
    result = types.ParsedDocument(body=[])
    for document_content in document.iter_inner_content():
        if isinstance(document_content, docx.text.paragraph.Paragraph):
            if docx_util.is_title(document_content):
                result.body.append(element_processor.process_title(document_content))
            elif docx_util.is_list_block(document_content):
                result.body.append(
                    element_processor.process_list_item(document_content)
                )
            else:
                for para in document_content.iter_inner_content():
                    if isinstance(para, docx.text.hyperlink.Hyperlink):
                        result.body.append(element_processor.process_hyperlink(para))

                    elif isinstance(para, docx.text.run.Run):
                        for para_content in para.iter_inner_content():
                            if isinstance(para_content, str):
                                text_run = element_processor.process_text_run(
                                    text=para_content,
                                    font=para.font,
                                )
                                if text_run:
                                    result.body.append(text_run)

                            elif isinstance(para_content, docx.drawing.Drawing):
                                result.body.append(
                                    element_processor.process_image(
                                        drawing=para_content
                                    )
                                )

        elif isinstance(document_content, docx.table.Table):
            table = element_processor.process_table(document_content)
            result.body.append(table)

    return result
