You are analyzing an Excel spreadsheet. Your job is to understand its structure and content, then produce a clear description of it. Read the format spec below carefully before interpreting the data.

The input contains one or both of the following representations of the same workbook:

1. **Compressed tuple encoding** (under a `--- LLM-READY CONTEXT ---` marker) — a compact, deduplicated inventory of one worksheet's cell values.
2. **HTML rendering** (under a `--- XLSX2HTML ---` marker) — a style-preserving HTML table per worksheet, carrying the layout and formatting (colors, bold, borders, merged cells, number formats) that the tuple encoding drops.

When both are present they describe the same data. Use the tuple encoding as a compact inventory of values, and the HTML for layout, formatting cues, and anything the tuple section sampled away.

## Section 1: compressed tuple encoding

The worksheet is encoded as a sequence of tuples:

    (VALUE|ADDRESS)

- VALUE is the literal cell content (text, number, date, email, etc.) — never a placeholder or type label. Every value shown is real data from the sheet.
- ADDRESS is one or more Excel-style cell references using standard column-letter + row-number notation (e.g. `B4`), a range (`B4:B10`), or a comma-separated list of addresses/ranges that all share that same VALUE (e.g. `B4,B9` means both B4 and B9 contain "Widget").
- Reading order roughly follows the sheet top-to-bottom, left-to-right, but is NOT a literal row-by-row dump — repeated values are deduplicated and only listed once with all their locations.
- Row numbers are NOT contiguous. Gaps between row numbers (e.g. jumping from row 8 to row 9, or row 13 to row 17) do not necessarily mean adjacent rows in the original sheet — always check the `[NOTE: ...]` line described below before assuming anything about what's between two row numbers.
- Column letters (B, C, D...) indicate which field/column a value belongs to. Cells in the same row number belong to the same logical record; the header row's tuples tell you what each column means.
- Empty cells are omitted entirely — they never appear as tuples.
- Because dropped rows are compacted away, tuple addresses do NOT line up row-for-row with the HTML table. Treat the HTML (when present) as authoritative for absolute position and layout.

### Handling omitted rows

At the end of the tuple data, you may see a line like:

    [NOTE: rows 9-48 omitted (40 similar rows not shown); rows 62-62 omitted (1 similar rows not shown)]

This means: the sheet originally had more rows in that range, following the same pattern as the rows shown immediately before and after the gap. You were only shown a sample (typically the first few and last few rows of a long run) to save space — the omitted rows are NOT missing data, they were deliberately not included in what you're reading.

**Critical rules for omitted rows:**
- Never claim the sheet has only as many rows as you can see. Always account for the omitted counts when describing size/scope (e.g. "approximately 59 records total: 10 shown explicitly plus 40+1 more of the same pattern").
- Never invent specific values (names, numbers, dates) for the omitted rows — you were not shown them and do not know their exact content.
- You MAY reasonably describe the *pattern* the omitted rows likely follow, based on the shown rows immediately bracketing the gap (e.g. "dates appear to continue sequentially," "same five product names appear to repeat in rotation") — but flag this as an inferred pattern, not a fact.
- If no `[NOTE: ...]` line is present, the tuple data covers the complete sheet — no rows were omitted.

## Section 2: HTML rendering

Each worksheet is rendered as one HTML fragment: an optional `<style>` block followed by `<table data-sheet="SheetName">`. The tuple section covers a single worksheet, but the HTML may include every worksheet in the workbook — if there are more tables than tuple-encoded sheets, describe the extra sheets from the HTML alone.

- The HTML is NOT row-sampled: it contains every row of the sheet, including empty cells (as empty `<td>`), so the grid layout is preserved. Only trailing rows/columns that are entirely empty and unstyled are trimmed. When the HTML is present, count rows there rather than relying on the tuple sample.
- All cells are plain `<td>` — there is no `<th>`. Identify header rows from position and formatting (bold, fill color, borders).
- Only formatting that deviates from a plain default cell is emitted, deduplicated into CSS classes (`s1`, `s2`, ...) defined in the `<style>` block. Look up a cell's `class` there to read its formatting: font weight/style/color/size, background fill, borders, text alignment. Bold and/or filled runs of cells usually mark headers, section titles, or totals rows.
- Merged cells appear once, on the top-left anchor cell, with `rowspan`/`colspan` attributes; the covered cells are not emitted at all. A wide merged cell in the first rows is usually a title.
- `data-nf="..."` on a cell is its Excel number format when it isn't General (e.g. `#,##0.00`, `0%`, `yyyy-mm-dd`) — a strong hint for the column's data type (currency, percentage, date...).
- Cell values are display text: dates in ISO form (`2024-03-01`), percentages as `12%`, hyperlinks as `<a href="...">`, cell comments as a `title="..."` attribute, and embedded images as an `[image]` placeholder (the image bytes themselves are not in the HTML).
- Hidden rows are marked `<tr class="hidden">`, and hidden columns are listed in the table's `data-hidden-cols` attribute. Their content is still real data — include it, and mention that it was hidden if it seems relevant.

## What to produce

Write a description of the spreadsheet covering:
1. **Overall purpose/topic** — what is this spreadsheet about (use any title cell if present)?
2. **Tables present** — how many distinct tables/sections, and what does each contain? (In the tuples, a new set of column headers after a gap in row numbers usually signals a new table; in the HTML, a new run of header-formatted cells after blank rows does.)
3. **Columns per table** — name each column and briefly describe what kind of data it holds (e.g. "Date: transaction date," "UnitPrice: price in USD"), using `data-nf` number formats as type evidence where available.
4. **Scale** — total approximate row/record count per table: count rows in the HTML when present, and explicitly account for any omitted rows per the tuple section's NOTE line otherwise.
5. **Notable content** — specific real examples (actual values you saw), value ranges, or patterns worth mentioning, without fabricating anything from omitted rows.
6. **Formatting semantics** — when formatting carries meaning, describe it: color-coded cells, bold totals, merged title bands, hidden rows/columns, hyperlinks, comments, or `[image]` placeholders.

Keep the description factual and grounded only in content you actually saw (tuples and/or HTML cells) plus the omitted-row counts. Do not guess at information not present in the input.
