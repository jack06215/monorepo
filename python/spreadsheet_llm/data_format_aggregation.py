"""
data_format_aggregation.py

Module 3 of SheetCompressor (paper Section 3.4 + Appendix M.1):
"Data-format-aware Aggregation"

Idea: adjacent numeric/date/etc. cells usually share a format. Exact values
matter less than knowing "this region is a Date column" or "this region is
Currency". We:
  1. Map each non-empty cell to a coarse data type (Year, Integer, Float,
     Percentage, Scientific, Date, Time, Currency, Email, String, Other)
     using the cell's Number Format String (NFS) first, falling back to a
     rule-based value sniff if NFS is "General"/absent.
  2. Flood-fill (BFS/DFS) connected regions of cells sharing the same data
     type into rectangular-ish clusters (Algorithm 1 in Appendix M.1).
  3. Replace each cluster with a single representative "type label" cell
     value (e.g. "IntNum", "DateData") spanning that address range, which
     downstream translation (Module 2) will render as one dictionary entry.

Text/string cells are intentionally left alone (data type "String") and are
NOT aggregated by value here -- only same-format numeric/date/etc. runs are
collapsed, matching the paper (semantic clustering of strings like
"China"/"France" -> "Country" is explicitly listed as future work).
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from python.spreadsheet_llm.sheet_model import Cell, Sheet

# ---- Step 1: map a cell to a coarse data type -----------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SCI_RE = re.compile(r"^-?\d(\.\d+)?[eE][+-]?\d+$")

# Keywords in NFS strings that signal a semantic type.
_NFS_TYPE_HINTS = [
    ("yyyy", "DateData"),
    ("yy", "DateData"),
    ("mmm", "DateData"),
    ("dd", "DateData"),
    ("m/d", "DateData"),
    ("h:mm", "TimeData"),
    ("hh:mm", "TimeData"),
    ("ss", "TimeData"),
    ("%", "PercentageData"),
    ("$", "CurrencyData"),
    ("€", "CurrencyData"),
    ("£", "CurrencyData"),
    ("0.00e+00", "ScientificNum"),
    ("e+", "ScientificNum"),
]


def infer_data_type(cell: Cell) -> str:
    """Return one of the paper's predefined type labels for a non-empty cell."""
    if cell.is_empty:
        return "Empty"

    nfs = (cell.number_format or "General").lower()

    # 1) Trust an explicit Number Format String first.
    for hint, label in _NFS_TYPE_HINTS:
        if hint in nfs:
            return label

    val = cell.value

    # 2) Fall back to sniffing the raw value.
    if isinstance(val, bool):
        return "String"  # bools rendered as text labels, not aggregated numerically
    if isinstance(val, int):
        if 1000 <= val <= 3000 and nfs == "general" and len(str(val)) == 4:
            return "YearData"
        return "IntNum"
    if isinstance(val, float):
        return "FloatNum"
    if hasattr(val, "isoformat"):  # datetime/date/time objects
        # date vs datetime vs time
        import datetime

        if isinstance(val, datetime.time):
            return "TimeData"
        return "DateData"
    if isinstance(val, str):
        s = val.strip()
        if _EMAIL_RE.match(s):
            return "EmailData"
        if _SCI_RE.match(s):
            return "ScientificNum"
        # numeric-looking strings
        try:
            float(s.replace(",", ""))
            return "FloatNum" if "." in s else "IntNum"
        except ValueError:
            pass
        return "String"

    return "Other"


# ---- Step 2 + 3: flood-fill clusters of same type, replace with label -----


@dataclass
class AggregatedRegion:
    top: int
    left: int
    bottom: int
    right: int
    data_type: str

    @property
    def is_single_cell(self) -> bool:
        return self.top == self.bottom and self.left == self.right


def _neighbors(r: int, c: int):
    yield r - 1, c
    yield r + 1, c
    yield r, c - 1
    yield r, c + 1


def aggregate_by_data_format(
    sheet: Sheet,
) -> Tuple[List[AggregatedRegion], Dict[Tuple[int, int], str]]:
    """
    Flood-fills connected same-data-type regions (4-connectivity), per
    Appendix M.1 Algorithm 1. Only aggregates non-"String" numeric/date/etc.
    types with more than one cell -- single cells and text are kept as-is so
    real content (headers, labels) isn't destroyed.

    Returns:
      regions: list of AggregatedRegion covering the whole grid (including
               single String/empty cells as 1x1 regions) for downstream use.
      cell_type_map: (row, col) -> data_type, useful for debugging/tests.
    """
    n_rows, n_cols = sheet.n_rows, sheet.n_cols
    visited = [[False] * (n_cols + 1) for _ in range(n_rows + 1)]
    type_map: Dict[Tuple[int, int], str] = {}
    for r in range(1, n_rows + 1):
        for c in range(1, n_cols + 1):
            type_map[(r, c)] = infer_data_type(sheet.get(r, c))

    regions: List[AggregatedRegion] = []

    # Types eligible for merging into a region label (exact text is NOT
    # aggregated -- keep individual strings so meaning isn't lost).
    AGGREGATABLE = {
        "IntNum",
        "FloatNum",
        "YearData",
        "DateData",
        "TimeData",
        "PercentageData",
        "CurrencyData",
        "ScientificNum",
        "EmailData",
    }

    for r in range(1, n_rows + 1):
        for c in range(1, n_cols + 1):
            if visited[r][c]:
                continue
            cur_type = type_map[(r, c)]

            if cur_type not in AGGREGATABLE:
                # String / Empty / Other: emit as its own 1x1 region, unmerged.
                visited[r][c] = True
                regions.append(AggregatedRegion(r, c, r, c, cur_type))
                continue

            # BFS flood-fill same-type connected region.
            stack = [(r, c)]
            visited[r][c] = True
            cells_in_region = [(r, c)]
            while stack:
                cr, cc = stack.pop()
                for nr, nc in _neighbors(cr, cc):
                    if 1 <= nr <= n_rows and 1 <= nc <= n_cols and not visited[nr][nc]:
                        if type_map[(nr, nc)] == cur_type:
                            visited[nr][nc] = True
                            stack.append((nr, nc))
                            cells_in_region.append((nr, nc))

            top = min(x[0] for x in cells_in_region)
            bottom = max(x[0] for x in cells_in_region)
            left = min(x[1] for x in cells_in_region)
            right = max(x[1] for x in cells_in_region)

            if len(cells_in_region) == 1:
                # Lone numeric cell: not worth abstracting away, keep concrete
                # (paper still benefits more from clustering runs of 2+).
                regions.append(AggregatedRegion(top, left, bottom, right, cur_type))
            else:
                regions.append(AggregatedRegion(top, left, bottom, right, cur_type))

    return regions, type_map
