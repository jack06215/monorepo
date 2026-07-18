"""
structural_anchors.py

Module 1 of SheetCompressor (paper Section 3.2 + Appendix C):
"Structural-anchor-based Extraction"

Idea: large spreadsheets contain many homogeneous rows/columns that add
little to layout understanding. We find heterogeneous rows/columns
("structural anchors") -- likely table boundaries/headers -- keep a
k-row/column neighborhood around each anchor, and discard everything else,
then remap coordinates so the remaining cells are contiguous.

This is a lightweight heuristic version of Appendix C: instead of the full
candidate-boundary search with borders/fill/font, we detect heterogeneity by
comparing each row/column's "signature" (values + number formats) against
its neighbors. This keeps the implementation self-contained while following
the same anchor -> k-neighborhood -> extract -> remap pipeline described in
the paper.
"""

from dataclasses import dataclass, replace
from typing import List, Set, Tuple

from packages.spreadsheet_llm.sheet_model import Sheet


def _row_signature(sheet: Sheet, row: int) -> Tuple:
    """A coarse fingerprint of a row: which columns are non-empty + their formats.

    Bold is included so style-only header rows (same "General" format as the
    body below them) still register as boundaries. Fill/color deliberately
    are NOT part of the signature: alternating-fill "zebra" body rows would
    otherwise make every row look like a boundary and defeat extraction.
    """
    sig = []
    for c in range(1, sheet.n_cols + 1):
        cell = sheet.get(row, c)
        if cell.is_empty:
            sig.append(None)
        else:
            sig.append((cell.number_format, cell.bold))
    return tuple(sig)


def _col_signature(sheet: Sheet, col: int) -> Tuple:
    sig = []
    for r in range(1, sheet.n_rows + 1):
        cell = sheet.get(r, col)
        if cell.is_empty:
            sig.append(None)
        else:
            sig.append((cell.number_format, cell.bold))
    return tuple(sig)


def _is_heterogeneous(sig_a: Tuple, sig_b: Tuple) -> bool:
    """
    Two adjacent row/column signatures are considered heterogeneous (i.e. one
    of them likely marks a boundary) if they differ meaningfully: different
    emptiness pattern, or different format types in more than a small
    fraction of overlapping cells.
    """
    if len(sig_a) != len(sig_b):
        return True
    n = len(sig_a)
    if n == 0:
        return False
    diff = sum(1 for a, b in zip(sig_a, sig_b) if a != b)
    return (diff / n) > 0.15  # >15% of cells changed emptiness/format -> boundary-like


def find_row_anchors(sheet: Sheet) -> Set[int]:
    """Rows that differ notably from the row above or below them."""
    anchors = set()
    sigs = [None] + [_row_signature(sheet, r) for r in range(1, sheet.n_rows + 1)]
    for r in range(1, sheet.n_rows + 1):
        prev_sig = sigs[r - 1] if r - 1 >= 1 else None
        next_sig = sigs[r + 1] if r + 1 <= sheet.n_rows else None
        cur_sig = sigs[r]
        is_anchor = False
        if prev_sig is None or _is_heterogeneous(cur_sig, prev_sig):
            is_anchor = True
        if next_sig is None or _is_heterogeneous(cur_sig, next_sig):
            is_anchor = True
        # A totally empty row is not an anchor (it's homogeneous "nothing").
        if all(v is None for v in cur_sig):
            is_anchor = False
        if is_anchor:
            anchors.add(r)
    return anchors


def find_col_anchors(sheet: Sheet) -> Set[int]:
    """Columns that differ notably from the column to the left or right of them."""
    anchors = set()
    sigs = [None] + [_col_signature(sheet, c) for c in range(1, sheet.n_cols + 1)]
    for c in range(1, sheet.n_cols + 1):
        prev_sig = sigs[c - 1] if c - 1 >= 1 else None
        next_sig = sigs[c + 1] if c + 1 <= sheet.n_cols else None
        cur_sig = sigs[c]
        is_anchor = False
        if prev_sig is None or _is_heterogeneous(cur_sig, prev_sig):
            is_anchor = True
        if next_sig is None or _is_heterogeneous(cur_sig, next_sig):
            is_anchor = True
        if all(v is None for v in cur_sig):
            is_anchor = False
        if is_anchor:
            anchors.add(c)
    return anchors


@dataclass
class ExtractionResult:
    kept_rows: List[int]  # original row indices retained, sorted
    kept_cols: List[int]  # original col indices retained, sorted
    row_map: dict  # original row -> new (remapped) row
    col_map: dict  # original col -> new (remapped) col
    sheet: Sheet  # the new, smaller Sheet with remapped coordinates


def extract_structural_anchors(sheet: Sheet, k: int = 4) -> ExtractionResult:
    """
    Paper Eq. (3)-(5): find anchor rows/cols, keep rows/cols within k of any
    anchor, drop the rest, and remap coordinates to be contiguous again.

    k=4 is the value the paper found optimal (Appendix D.1: k=4 preserves
    >97% of true table boundary rows/columns while maximizing F1).
    """
    row_anchors = find_row_anchors(sheet)
    col_anchors = find_col_anchors(sheet)

    kept_rows = sorted(
        r
        for r in range(1, sheet.n_rows + 1)
        if any(abs(r - a) <= k for a in row_anchors)
    )
    kept_cols = sorted(
        c
        for c in range(1, sheet.n_cols + 1)
        if any(abs(c - a) <= k for a in col_anchors)
    )

    # Fallback: if heuristics found nothing (e.g. tiny/uniform sheet), keep everything.
    if not kept_rows:
        kept_rows = list(range(1, sheet.n_rows + 1))
    if not kept_cols:
        kept_cols = list(range(1, sheet.n_cols + 1))

    row_map = {orig: new for new, orig in enumerate(kept_rows, start=1)}
    col_map = {orig: new for new, orig in enumerate(kept_cols, start=1)}

    new_grid = []
    for orig_r in kept_rows:
        new_row = []
        for orig_c in kept_cols:
            src = sheet.get(orig_r, orig_c)
            # replace() keeps every other field (value, formats, styling)
            # so formatting survives extraction for downstream rendering.
            new_row.append(replace(src, row=row_map[orig_r], col=col_map[orig_c]))
        new_grid.append(new_row)

    new_sheet = Sheet(new_grid, len(kept_rows), len(kept_cols), name=sheet.name)

    return ExtractionResult(
        kept_rows=kept_rows,
        kept_cols=kept_cols,
        row_map=row_map,
        col_map=col_map,
        sheet=new_sheet,
    )
