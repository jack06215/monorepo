You are analyzing a compressed representation of an Excel spreadsheet. Your job is to understand its structure and content, then produce a clear description of it. Read the format spec below carefully before interpreting the data.

## Format spec

The spreadsheet is encoded as a sequence of tuples:

    (VALUE|ADDRESS)

- VALUE is the literal cell content (text, number, date, email, etc.) — never a placeholder or type label. Every value shown is real data from the sheet.
- ADDRESS is one or more Excel-style cell references using standard column-letter + row-number notation (e.g. `B4`), a range (`B4:B10`), or a comma-separated list of addresses/ranges that all share that same VALUE (e.g. `B4,B9` means both B4 and B9 contain "Widget").
- Reading order roughly follows the sheet top-to-bottom, left-to-right, but is NOT a literal row-by-row dump — repeated values are deduplicated and only listed once with all their locations.
- Row numbers are NOT contiguous. Gaps between row numbers (e.g. jumping from row 8 to row 9, or row 13 to row 17) do not necessarily mean adjacent rows in the original sheet — always check the `[NOTE: ...]` line described below before assuming anything about what's between two row numbers.
- Column letters (B, C, D...) indicate which field/column a value belongs to. Cells in the same row number belong to the same logical record; the header row's tuples tell you what each column means.
- Empty cells are omitted entirely — they never appear as tuples.

## Handling omitted rows

At the end of the data, you may see a line like:

    [NOTE: rows 9-48 omitted (40 similar rows not shown); rows 62-62 omitted (1 similar rows not shown)]

This means: the sheet originally had more rows in that range, following the same pattern as the rows shown immediately before and after the gap. You were only shown a sample (typically the first few and last few rows of a long run) to save space — the omitted rows are NOT missing data, they were deliberately not included in what you're reading.

**Critical rules for omitted rows:**
- Never claim the sheet has only as many rows as you can see. Always account for the omitted counts when describing size/scope (e.g. "approximately 59 records total: 10 shown explicitly plus 40+1 more of the same pattern").
- Never invent specific values (names, numbers, dates) for the omitted rows — you were not shown them and do not know their exact content.
- You MAY reasonably describe the *pattern* the omitted rows likely follow, based on the shown rows immediately bracketing the gap (e.g. "dates appear to continue sequentially," "same five product names appear to repeat in rotation") — but flag this as an inferred pattern, not a fact.
- If no `[NOTE: ...]` line is present, the data shown is the complete sheet — no rows were omitted.

## What to produce

Write a description of the spreadsheet covering:
1. **Overall purpose/topic** — what is this spreadsheet about (use any title cell if present)?
2. **Tables present** — how many distinct tables/sections, and what does each contain? (A new set of column headers after a gap in row numbers usually signals a new table.)
3. **Columns per table** — name each column and briefly describe what kind of data it holds (e.g. "Date: transaction date," "UnitPrice: price in USD").
4. **Scale** — total approximate row/record count per table, explicitly accounting for any omitted rows per the NOTE line.
5. **Notable content** — specific real examples (actual values you saw), value ranges, or patterns worth mentioning, without fabricating anything from omitted rows.

Keep the description factual and grounded only in tuples you actually saw plus the omitted-row counts. Do not guess at information not present in the input.
