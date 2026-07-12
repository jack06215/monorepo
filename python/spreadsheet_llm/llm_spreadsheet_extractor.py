"""
llm_spreadsheet_extractor.py

Zero-configuration entry point for the *lossless* encoding path: the full
Module 2 inverted-index translation (real values + [FORMATTING] index) with
no structural-anchor extraction, no row sampling, and no gap notes.

Equivalent to:
    python -m python.spreadsheet_llm.llm_context_encoder <file.xlsx> \
        --no-gap-notes --no-row-sampling --no-module1

Usage:
    python -m python.spreadsheet_llm.llm_spreadsheet_extractor
    python -m python.spreadsheet_llm.llm_spreadsheet_extractor my_file.xlsx
"""

import argparse

from python.spreadsheet_llm.llm_context_encoder import build_llm_context


def main():
    parser = argparse.ArgumentParser(
        description="Lossless spreadsheet encoder for LLM pipelines: every "
        "row is kept (no extraction, no sampling, no gap notes)."
    )
    parser.add_argument(
        "xlsx_path",
        nargs="?",
    )
    parser.add_argument(
        "--sheet", default=None, help="Sheet name (default: active sheet)"
    )
    args = parser.parse_args()

    result = build_llm_context(
        args.xlsx_path,
        sheet_name=args.sheet,
        include_gap_notes=False,
        enable_row_sampling=False,
        enable_module1=False,
    )

    print(result.compressed_text)


if __name__ == "__main__":
    main()
