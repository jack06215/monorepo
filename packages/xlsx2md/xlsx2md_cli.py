"""CLI for Excel to Markdown conversion."""

import argparse
import os
import pathlib

import pydantic

from common import path_util
from xlsx2md import parser


class Args(pydantic.BaseModel):
    """Command line arguments."""

    folder_path: pathlib.Path
    output_path: pathlib.Path


def main(args: Args) -> None:
    """Main function."""
    for xlsx_file in path_util.iter_files(folder=args.folder_path, extensions=["xlsx"]):
        print(f"Processing {xlsx_file}...")
        try:
            md_processor = parser.Xlsx2Markdown(filename=xlsx_file.as_posix())
            res = md_processor.parse()
            with open(
                os.path.join(
                    args.output_path,
                    f"{xlsx_file.stem}.md",
                ),
                mode="w",
            ) as fp:
                for _, iter in enumerate(res):
                    fp.write(iter.to_markdown())
        except Exception as e:
            raise e


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
        help="Output folder path..",
        required=True,
    )
    args = Args(**vars(arg_parser.parse_args()))
    main(args)
