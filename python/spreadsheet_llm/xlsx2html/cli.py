"""CLI for Excel to HTML conversion."""

import argparse
import pathlib

import pydantic

from python.common import path_util
from python.spreadsheet_llm.xlsx2html import parser


class Args(pydantic.BaseModel):
    """Command line arguments."""

    folder_path: pathlib.Path
    output_path: pathlib.Path


def main(args: Args) -> None:
    """Convert every .xlsx under folder_path to one .html in output_path."""
    for xlsx_file in path_util.iter_files(folder=args.folder_path, extensions=["xlsx"]):
        print(f"Processing {xlsx_file}...")
        parsed_worksheets = parser.Xlsx2Html(filename=xlsx_file.as_posix()).parse()
        output_file = args.output_path / f"{xlsx_file.stem}.html"
        with open(output_file, mode="w") as fp:
            fp.write("\n".join(sheet.to_html() for sheet in parsed_worksheets))


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--folder_path",
        type=str,
        help="Folder path to XLSX files.",
        required=True,
    )
    arg_parser.add_argument(
        "--output_path",
        type=str,
        help="Output folder path.",
        required=True,
    )
    main(Args(**vars(arg_parser.parse_args())))
