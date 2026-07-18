"""
sheet_compressor.py

End-to-end SheetCompressor pipeline (paper Figure 1 / Figure 2):

  .xlsx file
      -> Sheet (dense grid, sheet_model.py)
      -> Module 1: structural-anchor-based extraction   (structural_anchors.py)
      -> Module 3: data-format-aware aggregation          (data_format_aggregation.py)
      -> Module 2: inverted-index translation             (inverted_index.py)
      -> compact text representation fed to an LLM

Note on ordering: the paper's Section 3 numbers the modules 1/2/3 as
Extraction -> Translation -> Aggregation, but Figure 2's worked example
extracts, THEN inverts, THEN aggregates. In our implementation we run
Extraction -> Aggregation -> Translation, because aggregation operates
most naturally on the still-2D grid (flood fill needs neighbors), and
translation is the final serialization step that turns whatever cell/region
values exist (aggregated or not) into the compact dictionary. This produces
an equivalent final artifact and matches the "vanilla -> skeleton ->
inverted+aggregated" progression shown in Figure 2.

Also exposes a rough token-count-based compression ratio (paper Eq. 9:
r = n / n'), using a simple whitespace/char heuristic by default and an
optional tiktoken-based exact GPT tokenizer count if installed.
"""

import argparse
from dataclasses import dataclass
from typing import Optional

from packages.spreadsheet_llm.data_format_aggregation import aggregate_by_data_format
from packages.spreadsheet_llm.inverted_index import (
    build_inverted_index,
    render_json_like,
    render_paper_style,
)
from packages.spreadsheet_llm.sheet_model import Sheet, load_xlsx
from packages.spreadsheet_llm.structural_anchors import (
    ExtractionResult,
    extract_structural_anchors,
)

# ---------------------------------------------------------------------------
# Vanilla encoding (Section 3.1) -- used as the "before" baseline for
# measuring compression ratio, exactly as the paper defines it.
# ---------------------------------------------------------------------------


def vanilla_encode(sheet: Sheet) -> str:
    """
    Markdown-like vanilla encoding: '|Address,Value|Address,Value|...\\n' per
    row, including empty cells. This is what the paper compresses FROM.
    """
    lines = []
    for r in range(1, sheet.n_rows + 1):
        parts = []
        for c in range(1, sheet.n_cols + 1):
            cell = sheet.get(r, c)
            val = "" if cell.is_empty else str(cell.value)
            parts.append(f"{cell.address},{val}")
        lines.append("|" + "|".join(parts) + "|")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------


def count_tokens(text: str) -> int:
    """
    Prefer an exact GPT tokenizer (tiktoken) if available; otherwise fall
    back to a whitespace/punctuation-based approximation (~4 chars/token is
    the common rule of thumb, but we do something slightly more careful).
    """
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        # Fallback approximation: chars / 4, floor at word count.
        approx = max(len(text.split()), len(text) // 4)
        return approx


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


@dataclass
class CompressionReport:
    vanilla_text: str
    compressed_text: str
    vanilla_tokens: int
    compressed_tokens: int
    compression_ratio: float
    extraction: ExtractionResult
    kept_rows: int
    kept_cols: int
    original_rows: int
    original_cols: int


def compress_sheet(
    sheet: Sheet,
    k: int = 4,
    use_aggregation: bool = True,
    output_style: str = "paper",  # "paper" | "json"
) -> CompressionReport:
    """Run the full 3-module SheetCompressor pipeline on an already-loaded Sheet."""

    vanilla_text = vanilla_encode(sheet)
    vanilla_tokens = count_tokens(vanilla_text)

    # Module 1: structural-anchor-based extraction
    extraction = extract_structural_anchors(sheet, k=k)
    small_sheet = extraction.sheet

    # Module 3: data-format-aware aggregation (on the now-compact grid)
    if use_aggregation:
        regions, _type_map = aggregate_by_data_format(small_sheet)
    else:
        # Degenerate "aggregation" where every cell is its own region,
        # useful for ablation (matches paper's "-w/o Aggregation" row).
        from data_format_aggregation import AggregatedRegion, infer_data_type

        regions = []
        for r in range(1, small_sheet.n_rows + 1):
            for c in range(1, small_sheet.n_cols + 1):
                cell = small_sheet.get(r, c)
                dtype = (
                    "Empty"
                    if cell.is_empty
                    else (
                        "String"
                        if infer_data_type(cell)
                        not in (
                            "IntNum",
                            "FloatNum",
                            "YearData",
                            "DateData",
                            "TimeData",
                            "PercentageData",
                            "CurrencyData",
                            "ScientificNum",
                            "EmailData",
                        )
                        else "String"  # force literal (non type-labeled) rendering
                    )
                )
                regions.append(AggregatedRegion(r, c, r, c, dtype))

    # Module 2: inverted-index translation (final serialization)
    index = build_inverted_index(small_sheet, regions)
    compressed_text = (
        render_paper_style(index)
        if output_style == "paper"
        else render_json_like(index)
    )
    compressed_tokens = count_tokens(compressed_text)

    ratio = vanilla_tokens / compressed_tokens if compressed_tokens else float("inf")

    return CompressionReport(
        vanilla_text=vanilla_text,
        compressed_text=compressed_text,
        vanilla_tokens=vanilla_tokens,
        compressed_tokens=compressed_tokens,
        compression_ratio=ratio,
        extraction=extraction,
        kept_rows=len(extraction.kept_rows),
        kept_cols=len(extraction.kept_cols),
        original_rows=sheet.n_rows,
        original_cols=sheet.n_cols,
    )


def compress_xlsx(
    path: str,
    sheet_name: Optional[str] = None,
    k: int = 4,
    use_aggregation: bool = True,
    output_style: str = "paper",
) -> CompressionReport:
    sheet = load_xlsx(path, sheet_name=sheet_name)
    return compress_sheet(
        sheet, k=k, use_aggregation=use_aggregation, output_style=output_style
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="SheetCompressor: compress an .xlsx sheet for LLM consumption "
        "(reimplementation of SpreadsheetLLM, Tian et al. 2024)."
    )
    parser.add_argument("xlsx_path", help="Path to the .xlsx file")
    parser.add_argument(
        "--sheet", default=None, help="Sheet name (default: active sheet)"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=4,
        help="Structural anchor neighborhood radius (paper default: 4)",
    )
    parser.add_argument(
        "--no-aggregation",
        action="store_true",
        help="Disable Module 3 (data-format aggregation)",
    )
    parser.add_argument(
        "--format", choices=["paper", "json"], default="paper", help="Output text style"
    )
    parser.add_argument(
        "--show-vanilla",
        action="store_true",
        help="Also print the vanilla (uncompressed) encoding",
    )
    args = parser.parse_args()

    report = compress_xlsx(
        args.xlsx_path,
        sheet_name=args.sheet,
        k=args.k,
        use_aggregation=not args.no_aggregation,
        output_style=args.format,
    )

    print("=" * 70)
    print(
        f"Original sheet:   {report.original_rows} rows x {report.original_cols} cols"
    )
    print(
        f"After extraction: {report.kept_rows} rows x {report.kept_cols} cols "
        f"({report.kept_rows * report.kept_cols} / {report.original_rows * report.original_cols} cells kept)"
    )
    print(f"Vanilla tokens:    {report.vanilla_tokens}")
    print(f"Compressed tokens: {report.compressed_tokens}")
    print(f"Compression ratio: {report.compression_ratio:.2f}x")
    print("=" * 70)

    if args.show_vanilla:
        print("\n--- VANILLA ENCODING ---")
        print(report.vanilla_text)

    print("\n--- COMPRESSED ENCODING ---")
    print(report.compressed_text)


if __name__ == "__main__":
    main()
