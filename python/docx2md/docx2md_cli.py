"""Command line interface for Docx to Markdown conversion."""

import argparse
import os
import pathlib

import docx
import pydantic

from common import path_util
from docx2md import formatter, parser, types


class Args(pydantic.BaseModel):
    """Command line arguments."""

    folder_path: pathlib.Path
    output_path: pathlib.Path


def main(args: Args) -> None:
    """Sample demonstration function."""
    conversion_config = types.ConversionConfig()
    element_processor = parser.DocxElementProcessor(config=conversion_config)
    md_formatter = formatter.MarkdownFormatter(config=conversion_config)

    for docx_file in path_util.iter_files(folder=args.folder_path, extensions=["docx"]):
        print(f"Processing {docx_file}...")
        docx_ = docx.Document(docx_file.as_posix())
        try:
            with open(
                os.path.join(
                    args.output_path,
                    f"{docx_file.stem}.md",
                ),
                "w",
            ) as fp:
                result = parser.parse(
                    document=docx_, element_processor=element_processor
                )
                md_formatter.output(result)
                fp.write(md_formatter.ofile.getvalue())
        except Exception as e:
            raise e


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--folder_path",
        type=str,
        help="Folder path to PPTX files.",
        required=True,
    )
    arg_parser.add_argument(
        "--output_path",
        type=str,
        help="Output folder path..",
        required=True,
    )
    args = Args(**vars(arg_parser.parse_args()))
    main(args)
