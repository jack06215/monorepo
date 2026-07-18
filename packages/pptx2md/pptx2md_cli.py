"""CLI for PowerPoint to Markdown conversion."""

import argparse
import os
import pathlib

import pptx
import pptx.exc
import pydantic

from common import path_util
from pptx2md import formatter, parser, types


class Args(pydantic.BaseModel):
    """Command line arguments."""

    folder_path: pathlib.Path
    output_path: pathlib.Path


def main(args: Args) -> None:
    """Main function."""
    # TODO[jack06215]: This function is only used for testing purposes.
    # google_drive_cli will use this sample to process the pptx conversion.
    for pptx_file in path_util.iter_files(folder=args.folder_path, extensions=["pptx"]):
        print(f"Processing {pptx_file}...")
        try:
            prs = pptx.Presentation(pptx_file.as_posix())
            config = types.ConversionConfig(
                enable_slides=False,
                disable_escaping=False,
                disable_notes=False,
            )
            md_format = formatter.MarkdownFormatter(config=config)
            parsed_presentation = parser.parse(
                config=config,
                prs=prs,
            )
            md_format.output(presentation_data=parsed_presentation)
            with open(
                os.path.join(
                    args.output_path,
                    f"{pptx_file.stem}.md",
                ),
                mode="w",
            ) as fp:
                fp.write(md_format.ofile.getvalue())
        except pptx.exc.PackageNotFoundError as e:
            print(f"Error processing {pptx_file}: {e}")
            continue


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
