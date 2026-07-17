"""Parse whisper-stream style transcript where timestamps reset per section.
Build a global (absolute) timeline + LLM-friendly JSON, with incremental state."""

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
from typing import Any

TS_RE = re.compile(
    r"^\[(?P<s>\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(?P<e>\d{2}:\d{2}:\d{2}\.\d{3})\]\s*(?P<body>.*)$"
)
TT_RE = re.compile(r"\[_TT_(?P<tt>\d+)\]")
BEG_RE = re.compile(r"\[_BEG_\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def hms_ms_to_ms(hms: str) -> int:
    # "HH:MM:SS.mmm" -> milliseconds
    hh = int(hms[0:2])
    mm = int(hms[3:5])
    ss = int(hms[6:8])
    mmm = int(hms[9:12])
    return (((hh * 60 + mm) * 60) + ss) * 1000 + mmm


def ms_to_hms_ms(ms: int) -> str:
    if ms < 0:
        ms = 0
    total_seconds, mmm = divmod(ms, 1000)
    hh, rem = divmod(total_seconds, 3600)
    mm, ss = divmod(rem, 60)
    return f"{hh:02d}:{mm:02d}:{ss:02d}.{mmm:03d}"


def clean_text(body: str) -> tuple[str, dict[str, Any]]:
    """
    Remove markers like [_BEG_], [_TT_###] from text for LLM consumption,
    but return metadata about what was removed.
    """
    meta: dict[str, Any] = {}

    tt_m = TT_RE.search(body)
    if tt_m:
        meta["tt"] = int(tt_m.group("tt"))
    meta["has_beg"] = bool(BEG_RE.search(body))

    cleaned = BEG_RE.sub("", body)
    cleaned = TT_RE.sub("", cleaned)
    cleaned = cleaned.strip()

    # normalize internal multiple spaces (keep Japanese text intact)
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned, meta


@dataclasses.dataclass
class Segment:
    local_start_ms: int
    local_end_ms: int
    abs_start_ms: int
    abs_end_ms: int
    text: str
    raw_body: str
    meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_start_ms": self.local_start_ms,
            "local_end_ms": self.local_end_ms,
            "local_start": ms_to_hms_ms(self.local_start_ms),
            "local_end": ms_to_hms_ms(self.local_end_ms),
            "abs_start_ms": self.abs_start_ms,
            "abs_end_ms": self.abs_end_ms,
            "abs_start": ms_to_hms_ms(self.abs_start_ms),
            "abs_end": ms_to_hms_ms(self.abs_end_ms),
            "text": self.text,
            "raw_body": self.raw_body,
            "meta": self.meta,
        }


def parse_line(line: str) -> tuple[int, int, str, str, dict[str, Any]] | None:
    """
    Returns (local_start_ms, local_end_ms, cleaned_text, raw_body, meta) or None.
    """
    line = line.rstrip("\n")
    if not line.strip():
        return None

    m = TS_RE.match(line.strip())
    if not m:
        return None

    s_ms = hms_ms_to_ms(m.group("s"))
    e_ms = hms_ms_to_ms(m.group("e"))
    body = m.group("body").rstrip()

    cleaned, meta = clean_text(body)
    return s_ms, e_ms, cleaned, body, meta


def split_into_sections(text: str) -> list[list[str]]:
    """
    Primary rule: blank lines separate sections.
    """
    lines = text.splitlines()
    sections: list[list[str]] = []
    cur: list[str] = []

    for ln in lines:
        if ln.strip() == "":
            if cur:
                sections.append(cur)
                cur = []
            continue
        cur.append(ln)

    if cur:
        sections.append(cur)
    return sections


def build_sections(
    section_lines: list[list[str]],
    base_abs_offset_ms: int,
    section_start_index: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """
    Convert sections -> JSON dicts.
    Returns (sections_json, flat_segments_json, new_abs_offset_ms)
    """
    out_sections: list[dict[str, Any]] = []
    out_segments: list[dict[str, Any]] = []

    abs_offset = base_abs_offset_ms

    for i, lines in enumerate(section_lines):
        segs: list[Segment] = []
        local_max_end = 0

        for ln in lines:
            parsed = parse_line(ln)
            if not parsed:
                continue
            ls, le, cleaned, raw_body, meta = parsed
            if le > local_max_end:
                local_max_end = le
            segs.append(
                Segment(
                    local_start_ms=ls,
                    local_end_ms=le,
                    abs_start_ms=abs_offset + ls,
                    abs_end_ms=abs_offset + le,
                    text=cleaned,
                    raw_body=raw_body,
                    meta=meta,
                )
            )

        if not segs:
            # empty/garbage section; skip but don't change offsets
            continue

        # section duration is max local end time
        sec_abs_start = abs_offset
        sec_abs_end = abs_offset + local_max_end
        sec_text = " ".join(s.text for s in segs if s.text).strip()

        section_index = section_start_index + len(out_sections)

        sec_obj = {
            "section_index": section_index,
            "abs_start_ms": sec_abs_start,
            "abs_end_ms": sec_abs_end,
            "abs_start": ms_to_hms_ms(sec_abs_start),
            "abs_end": ms_to_hms_ms(sec_abs_end),
            "duration_ms": local_max_end,
            "full_text": sec_text,
            "segments": [s.to_dict() for s in segs],
        }
        out_sections.append(sec_obj)

        for s in segs:
            seg_obj = s.to_dict()
            seg_obj["section_index"] = section_index
            out_segments.append(seg_obj)

        abs_offset = sec_abs_end  # accumulate

    return out_sections, out_segments, abs_offset


def make_llm_chunks(
    flat_segments: list[dict[str, Any]],
    max_chars: int = 3500,
    max_gap_ms: int = 15_000,
) -> list[dict[str, Any]]:
    """
    Build LLM-friendly chunks by concatenating consecutive segments until:
    - char budget is exceeded, or
    - time gap between segments is too large
    """
    chunks: list[dict[str, Any]] = []
    buf: list[str] = []
    start_ms: int | None = None
    end_ms: int | None = None
    section_ids: list[int] = []
    last_end: int | None = None

    def flush() -> None:
        nonlocal buf, start_ms, end_ms, section_ids, last_end
        if not buf or start_ms is None or end_ms is None:
            buf = []
            start_ms = None
            end_ms = None
            section_ids = []
            last_end = None
            return
        txt = " ".join(x for x in buf if x).strip()
        if txt:
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "abs_start_ms": start_ms,
                    "abs_end_ms": end_ms,
                    "abs_start": ms_to_hms_ms(start_ms),
                    "abs_end": ms_to_hms_ms(end_ms),
                    "section_indices": sorted(set(section_ids)),
                    "text": txt,
                    "char_len": len(txt),
                }
            )
        buf = []
        start_ms = None
        end_ms = None
        section_ids = []
        last_end = None

    for seg in flat_segments:
        txt = seg.get("text", "")
        if not txt:
            continue

        s_ms = int(seg["abs_start_ms"])
        e_ms = int(seg["abs_end_ms"])
        sec_idx = int(seg.get("section_index", -1))

        if start_ms is None:
            start_ms = s_ms
            end_ms = e_ms
            last_end = e_ms
            section_ids = [sec_idx] if sec_idx >= 0 else []
            buf = [txt]
            continue

        gap = s_ms - (last_end if last_end is not None else s_ms)
        candidate = (" ".join(buf) + " " + txt).strip()

        if gap > max_gap_ms or len(candidate) > max_chars:
            flush()
            start_ms = s_ms
            end_ms = e_ms
            last_end = e_ms
            section_ids = [sec_idx] if sec_idx >= 0 else []
            buf = [txt]
            continue

        buf.append(txt)
        end_ms = max(end_ms, e_ms) if end_ms is not None else e_ms
        last_end = e_ms
        if sec_idx >= 0:
            section_ids.append(sec_idx)

    flush()
    return chunks


def load_state(path: str) -> dict[str, Any]:
    if not path or not os.path.exists(path):
        return {
            "version": 1,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "source_path": None,
            "last_byte_offset": 0,
            "tail_buffer": "",
            "abs_offset_ms": 0,
            "section_count": 0,
            "sections": [],
            "segments": [],
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def read_incremental(source_path: str, state: dict[str, Any]) -> tuple[str, int]:
    """
    Read only appended bytes from source_path based on state['last_byte_offset'].
    If the file shrank, reset offset.
    """
    last_off = int(state.get("last_byte_offset", 0) or 0)
    cur_size = os.path.getsize(source_path)

    if cur_size < last_off:
        # file rotated/truncated
        last_off = 0

    with open(source_path, "rb") as f:
        f.seek(last_off)
        new_bytes = f.read()

    try:
        new_text = new_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # fall back; still okay for most Japanese if the file is utf-8
        new_text = new_bytes.decode("utf-8", errors="replace")

    new_off = cur_size
    return new_text, new_off


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build global-timeline JSON from whisper transcript."
    )
    ap.add_argument(
        "--in", dest="inp", required=True, help="Input transcript text file"
    )
    ap.add_argument("--out", dest="outp", required=True, help="Output JSON file")
    ap.add_argument(
        "--state",
        dest="statep",
        required=True,
        help="State JSON file for incremental updates",
    )
    ap.add_argument(
        "--max-chars", type=int, default=3500, help="Max chars per llm_chunk"
    )
    ap.add_argument(
        "--max-gap-ms",
        type=int,
        default=15000,
        help="Time gap threshold to split chunks",
    )
    args = ap.parse_args()

    state = load_state(args.statep)
    state["source_path"] = os.path.abspath(args.inp)

    new_text, new_off = read_incremental(args.inp, state)
    combined = (state.get("tail_buffer", "") or "") + new_text

    # Split into blank-line sections
    raw_sections = split_into_sections(combined)

    # If the last section might be incomplete (common while file is still being written),
    # keep it in tail_buffer unless the input ends with a blank line.
    ends_with_blank = combined.endswith("\n\n") or combined.endswith("\r\n\r\n")
    complete_sections = raw_sections if ends_with_blank else raw_sections[:-1]
    tail_section = (
        "" if ends_with_blank else ("\n".join(raw_sections[-1]) if raw_sections else "")
    )

    base_abs_offset_ms = int(state.get("abs_offset_ms", 0) or 0)
    section_start_index = int(state.get("section_count", 0) or 0)

    new_sections, new_segments, new_abs_offset = build_sections(
        complete_sections,
        base_abs_offset_ms=base_abs_offset_ms,
        section_start_index=section_start_index,
    )

    # Update state
    state["updated_at"] = now_iso()
    state["last_byte_offset"] = new_off
    state["tail_buffer"] = tail_section
    state["abs_offset_ms"] = new_abs_offset

    state["sections"].extend(new_sections)
    state["segments"].extend(new_segments)
    state["section_count"] = len(state["sections"])

    # Build final output
    output: dict[str, Any] = {
        "version": 1,
        "generated_at": now_iso(),
        "source_path": state["source_path"],
        "stats": {
            "section_count": len(state["sections"]),
            "segment_count": len(state["segments"]),
            "abs_total_ms": int(state["abs_offset_ms"]),
            "abs_total": ms_to_hms_ms(int(state["abs_offset_ms"])),
        },
        "sections": state["sections"],
        "segments": state["segments"],
        "llm_chunks": make_llm_chunks(
            state["segments"],
            max_chars=args.max_chars,
            max_gap_ms=args.max_gap_ms,
        ),
    }

    save_json(args.outp, output)
    save_json(args.statep, state)


if __name__ == "__main__":
    main()
