"""
inverted_index.py

Module 2 of SheetCompressor (paper Section 3.3):
"Inverted-index Translation"

Idea: instead of walking the grid row-by-row and emitting every cell
(including empty ones and repeated values), build a dictionary keyed by
*value*, whose entries are the address (or address range) of every cell
holding that value. Empty cells are dropped entirely.

This module consumes the output of Module 3 (data-format-aware aggregation)
as its cell values: for aggregated numeric/date/etc. regions the "value" is
the type label (e.g. "IntNum"); for everything else it's the literal cell
text. That mirrors the paper's final combined pipeline (Fig. 2), where
translation happens *after* aggregation so type-labeled regions collapse
into single dictionary entries too.
"""

from collections import defaultdict
from typing import Dict, List

from openpyxl.utils import get_column_letter

from python.spreadsheet_llm.data_format_aggregation import AggregatedRegion
from python.spreadsheet_llm.sheet_model import Sheet


def _addr(row: int, col: int) -> str:
    return f"{get_column_letter(col)}{row}"


def _range_addr(region: AggregatedRegion) -> str:
    if region.is_single_cell:
        return _addr(region.top, region.left)
    return f"{_addr(region.top, region.left)}:{_addr(region.bottom, region.right)}"


def _region_display_value(sheet: Sheet, region: AggregatedRegion) -> str:
    """
    What text represents this region in the compressed output:
      - aggregated numeric/date/etc. region -> its type label (e.g. "IntNum")
      - single String/Other cell -> the literal cell value as text
      - Empty region -> None (caller should skip these entirely)
    """
    if region.data_type == "Empty":
        return None
    if region.data_type in ("String", "Other"):
        cell = sheet.get(region.top, region.left)
        val = cell.value
        return "" if val is None else str(val).strip()
    # Aggregated type-labeled region (IntNum, DateData, CurrencyData, ...)
    return region.data_type


def build_inverted_index(
    sheet: Sheet, regions: List[AggregatedRegion]
) -> "OrderedDictType":
    """
    Builds {value: [address_or_range, ...]} preserving first-seen order of
    values (so output is deterministic and roughly follows reading order).
    Empty regions are skipped (lossless w.r.t. non-empty content, per the
    paper: "empty cells excluded").
    """
    index: Dict[str, List[str]] = defaultdict(list)
    order: List[str] = []

    for region in regions:
        val = _region_display_value(sheet, region)
        if val is None or val == "":
            continue
        if val not in index:
            order.append(val)
        index[val].append(_range_addr(region))

    return {val: index[val] for val in order}


def render_json_like(index: dict, indent: int = 2) -> str:
    """
    Render the inverted index as the JSON-ish text the paper feeds to the
    LLM: {"Value": "Addr" or "Addr1,Addr2,..."}. Multiple disjoint
    occurrences of the same value are comma-joined rather than repeating the
    key (keeps it valid-ish JSON while staying compact).
    """
    lines = ["{"]
    items = list(index.items())
    for i, (val, addrs) in enumerate(items):
        addr_str = ",".join(addrs)
        safe_val = str(val).replace('"', "'")
        comma = "," if i < len(items) - 1 else ""
        lines.append(f'{" " * indent}"{safe_val}": "{addr_str}"{comma}')
    lines.append("}")
    return "\n".join(lines)


def render_paper_style(index: dict) -> str:
    """
    Render using the exact tuple-style format shown in the paper's own
    prompt templates (Appendix L.2):
        (Value|Address) or (Value|Address1,Address2) separated by nothing/space
    e.g.  (Year|A1)(IntNum|A2:B3)( |C4)
    This is the format actually fed to the LLM in their experiments.
    """
    parts = []
    for val, addrs in index.items():
        addr_str = ",".join(addrs)
        parts.append(f"({val}|{addr_str})")
    return "".join(parts)
