# SheetCompressor — a reimplementation of SpreadsheetLLM's encoding pipeline

Reimplements the core encoding framework from **"SpreadsheetLLM: Encoding
Spreadsheets for Large Language Models"** (Tian et al., Microsoft, 2024,
[arXiv:2407.09025](https://arxiv.org/abs/2407.09025)).

This is the *encoding* side of the paper (Section 3) — turning a real `.xlsx`
file into a compact text representation an LLM can consume — not the
fine-tuning or table-detection model training itself.

## Files

| File | Paper section | What it does |
|---|---|---|
| `sheet_model.py` | 3.1 | Loads an `.xlsx` via openpyxl into a dense `Sheet` of `Cell`s (handles merged cells, number formats) |
| `structural_anchors.py` | 3.2 + Appendix C | **Module 1**: finds heterogeneous "anchor" rows/columns, keeps a `k`-neighborhood around them, drops the rest, remaps coordinates |
| `data_format_aggregation.py` | 3.4 + Appendix M.1 | **Module 3**: infers a data type per cell (Int/Float/Date/Currency/%/Email/...) from its Number Format String or value, then flood-fills adjacent same-type cells into labeled regions |
| `inverted_index.py` | 3.3 | **Module 2**: builds a `{value: address_or_range}` dictionary, dropping empty cells and merging duplicate values — the final serialization step |
| `sheet_compressor.py` | Fig. 1/2, Eq. 9 | Orchestrates all three modules end-to-end, computes the vanilla-vs-compressed token compression ratio, and provides a CLI |
| `llm_context_encoder.py` | — | **Description-generation variant**: Modules 1+2 only (no aggregation, real values preserved) plus head/tail row sampling with explicit `[NOTE: rows X-Y omitted]` gap annotations — see below |
| `LLM_CONTEXT_ENCODER_INSTRUCTION.md` | — | The instruction prompt to pair with `llm_context_encoder.py` output when asking an LLM to describe a spreadsheet |
| `test_sheet_compressor.py` | — | 25 unit tests covering all modules |
| `test_llm_context_encoder.py` | — | 19 unit tests covering the description-generation variant (row sampling, gap annotation, no-silent-row-loss invariant) |
| `make_test_xlsx.py` | — | Generates the synthetic fixtures in `sample_data/` (`test_sheet.xlsx`: multi-table, mimics paper's Fig. 2; `big_sheet.xlsx`: 303-row single table that exercises row sampling/gap annotation) |
| `xlsx2html/` | — | Standalone openpyxl-native Excel → HTML converter that preserves cell metadata (font/fill colors, borders, merged ranges, number formats, hyperlinks, hidden rows/cols) as token-compact HTML with deduplicated CSS classes; images become `[image]` placeholders with base64 kept on the model |

## Usage

All commands run from the monorepo root (imports are monorepo-absolute):

```bash
# Regenerate the demo spreadsheets in sample_data/
poetry run python -m packages.spreadsheet_llm.make_test_xlsx

# Run the full paper pipeline (all 3 modules)
poetry run python -m packages.spreadsheet_llm.sheet_compressor \
    packages/spreadsheet_llm/sample_data/test_sheet.xlsx

# Run the LLM-description encoder (Modules 1+2 + row sampling, real values kept)
poetry run python -m packages.spreadsheet_llm.llm_context_encoder \
    packages/spreadsheet_llm/sample_data/big_sheet.xlsx

# Tests
poetry run python -m pytest packages/spreadsheet_llm/

# sheet_compressor options
poetry run python -m packages.spreadsheet_llm.sheet_compressor my_file.xlsx \
    --sheet "Sheet2" \        # pick a specific sheet (default: active)
    --k 4 \                   # structural-anchor neighborhood radius (paper default)
    --format paper \          # "paper" (tuple style) or "json" output
    --no-aggregation \        # ablation: disable Module 3
    --show-vanilla            # also print the uncompressed baseline
```

Programmatic use:

```python
from packages.spreadsheet_llm.sheet_compressor import compress_xlsx

report = compress_xlsx("my_file.xlsx", k=4)
print(report.compression_ratio)   # e.g. 12.97
print(report.compressed_text)     # what you'd send to the LLM
```

## Which entry point to use

- **`sheet_compressor.py`** — the paper-faithful pipeline (all 3 modules).
  Maximum compression, but Module 3 replaces runs of real values with type
  labels like `CurrencyData`. Right for table-detection/QA-style tasks.
- **`llm_context_encoder.py`** — for the description-generation/ingestion
  use case (LLM writes a natural-language description of the sheet, which
  then gets indexed into Elasticsearch). Skips Module 3 so the LLM sees
  real values, and instead thins long homogeneous row runs to head+tail
  samples with an explicit `[NOTE: rows X-Y omitted (N similar rows not
  shown)]` marker — including runs that Module 1 itself dropped, so no
  rows ever vanish unannotated. Pair its output with
  `LLM_CONTEXT_ENCODER_INSTRUCTION.md` as the LLM's instructions.

```python
from packages.spreadsheet_llm.llm_context_encoder import build_llm_context

result = build_llm_context("my_file.xlsx", k=4, sample_rows=5)
print(result.compressed_text)     # LLM-ready context, real values + gap notes
print(result.omitted_row_runs)    # [(start, end)] original rows not shown
```

## How the modules compose

```
.xlsx file
    │
    ▼
Sheet (dense m×n grid of Cells)
    │
    ▼
Module 1 — Structural-anchor extraction
  find heterogeneous rows/cols → keep k-neighborhood → drop rest → remap coords
    │  (paper: filters ~75% of content, keeps ~97% of true boundary rows/cols at k=4)
    ▼
Module 3 — Data-format-aware aggregation
  infer per-cell type (NFS-based, with value-sniffing fallback)
  → flood-fill same-type runs into regions → label with type (e.g. "DateData")
    │
    ▼
Module 2 — Inverted-index translation
  group by value/type-label → {value: "A1" or "A2:B10,C4"} → drop empties
    │
    ▼
Compact text:  (Header|B3)(DateData|C4:C13)(CurrencyData|E4:F13)...
```

**Note on module order:** the paper numbers modules 1/2/3 as
Extraction→Translation→Aggregation in prose, but its own Figure 2 example
runs Extraction→Translation→Aggregation visually while conceptually
aggregation and translation are interleaved (aggregated regions become
dictionary entries). This implementation runs **Extraction → Aggregation →
Translation**, since flood-fill aggregation needs 2D neighbor structure
(easiest before serialization), and translation is naturally the last,
purely-textual step. The output is equivalent in spirit and compression
behavior to the paper's pipeline.

## What's faithful vs. simplified

**Faithful to the paper:**
- Three-module structure and composition order/intent
- `k=4` default neighborhood (paper's ablation-chosen optimum, Appendix D.1)
- Predefined data types: Year, Integer, Float, Percentage, Scientific,
  Date, Time, Currency, Email (Section 3.4)
- Lossless lockstep for non-empty literal content — every non-empty
  original value is either preserved verbatim or represented by an
  aggregated type label, and no empty cells are ever emitted (Section 3.3)
- Compression ratio measured the same way (Eq. 9: `r = n / n'` in tokens)
- CLI ablation flag (`--no-aggregation`) reproduces the paper's finding
  that aggregation is the single largest compression contributor

**Simplified (noted in code comments):**
- **Structural-anchor detection** (Appendix C) uses a lightweight
  heterogeneity heuristic based on value/format signatures per row/column,
  rather than the paper's full candidate-boundary search that also
  considers cell borders, fill color, bold font, and pairwise overlap
  resolution. This captures the same core idea (skip long homogeneous
  runs, keep boundary regions) without the full CV-style boundary
  detector, which the paper itself notes only reaches 46.3% F1 on its own
  before the LLM refines it.
- **Semantic string clustering** (e.g. grouping "China"/"France" under
  "Country") is explicitly called out in the paper as *future work*, not
  implemented — and isn't implemented here either.
- No LLM fine-tuning, table-detection model, or Chain-of-Spreadsheet QA
  pipeline (Sections 3.5, 4) — this is the encoding/compression front-end
  only, which is the input format those downstream tasks consume.

