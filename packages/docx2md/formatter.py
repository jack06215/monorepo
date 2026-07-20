"""Markdown formatter for parsed docx."""

import io
import re
from typing import cast

from packages.docx2md import types


class MarkdownFormatter:
    """Parsed Presentation to Markdown text."""

    def __init__(self, config: types.ConversionConfig) -> None:
        """Constructor."""
        self.ofile = io.StringIO()
        self.esc_re1 = re.compile(r"([\\\*`!_\{\}\[\]\(\)#\+-\.])")
        self.esc_re2 = re.compile(r"(<[^>]+>)")
        self.config = config
        self.images_reference: list[str] = []

    def output(
        self,
        document_data: types.ParsedDocument,
    ) -> None:
        """Writes parsed presentation to StringIO."""
        image_idx = 1
        for element in document_data.body:
            match element.type:
                case "title":
                    element = cast(types.TitleElement, element)
                    element.content = element.content.strip()
                    if element.content:
                        self.put_title(element.content, element.level)
                case "list_item":
                    element = cast(types.ListItemElement, element)
                    self.put_list(
                        self.get_formatted_runs(element.content),
                        element.level,
                    )
                case "paragraph":
                    element = cast(types.ParagraphElement, element)
                    if element.content.type == "text_runs":
                        runs = cast(list[types.TextRun], element.content.data)
                        self.put_para(self.get_formatted_runs(runs))
                    elif element.content.type == "image":
                        img_str = cast(types.Image, element.content.data)
                        self.put_image_tag(image_idx)
                        self.images_reference.append(f"[image{image_idx}]:<{img_str}>")
                        image_idx += 1
                case "table":
                    element = cast(types.TableElement, element)
                    self.put_table(
                        [
                            [self.get_formatted_runs(cell) for cell in row]
                            for row in element.content
                        ]
                    )

        for i in range(len(self.images_reference)):
            self.ofile.write(self.images_reference[i] + "\n\n")

    def get_formatted_runs(self, runs: list[types.TextRun]) -> str:
        """Format list of text runs."""
        res = ""
        for run in runs:
            text = run.text
            if text == "":
                continue
            if not self.config.disable_escaping:
                text = self.get_escaped(text)
            if run.style.hyperlink:
                text = self.get_hyperlink(text, run.style.hyperlink)
            if run.style.is_accent:
                text = self.get_accent(text)
            elif run.style.is_strong:
                text = self.get_strong(text)

            res += text
        return res.strip()

    def put_title(self, text: str, level: int) -> None:
        """Write title."""
        self.ofile.write("#" * level + " " + text + "\n\n")

    def put_list(self, text: str, level: int) -> None:
        """Write list."""
        self.ofile.write("  " * level + "* " + text.strip() + "\n")

    def put_list_header(self) -> None:
        """Write list header."""
        self.put_para("")

    def put_para(self, text: str) -> None:
        """Write a paragraph."""
        self.ofile.write(text + "\n\n")

    def put_image_tag(
        self,
        number_label: int,
    ) -> None:
        """Add image reference tag."""
        self.ofile.write(f"![][image{number_label}]\n\n")

    def put_table(self, table: list[list[str]]) -> None:
        """Format table."""

        def gen_table_row(row: list[str]) -> str:
            return "| " + " | ".join([c.replace("\n", "<br />") for c in row]) + " |"

        self.ofile.write(gen_table_row(table[0]) + "\n")
        self.ofile.write(gen_table_row([":-:" for _ in table[0]]) + "\n")
        self.ofile.write("\n".join([gen_table_row(row) for row in table[1:]]) + "\n\n")

    def get_accent(self, text: str) -> str:
        """Format accent."""
        return " *" + text + "* "

    def get_strong(self, text: str) -> str:
        """Format bold text."""
        return " **" + text + "** "

    def get_hyperlink(self, text: str, url: str) -> str:
        """Format hyperlink."""
        return "[" + text + "](" + url + ")"

    def esc_repl(self, match: re.Match[str]) -> str:
        """Escapes a string."""
        return "\\" + match.group(0)

    def get_escaped(self, text: str) -> str:
        """Replace escaped characters."""
        text = re.sub(self.esc_re1, self.esc_repl, text)
        text = re.sub(self.esc_re2, self.esc_repl, text)
        return text
