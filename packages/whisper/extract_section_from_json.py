import argparse
import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

from common.execute import run_command

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Section:
    section_index: int
    abs_start: str
    abs_end: str
    full_text: str


def jq_cmd(inp: str, jq_filter: str, *, raw: bool) -> Sequence[str | int | float]:
    return ["jq", "-r" if raw else "-c", jq_filter, inp]


def build_selector(from_: int | None, to: int | None) -> str:
    base = ".sections[]"
    conds: list[str] = []
    if from_ is not None:
        conds.append(f".section_index >= {from_}")
    if to is not None:
        conds.append(f".section_index < {to}")
    if not conds:
        return base
    return f"{base} | select({' and '.join(conds)})"


def iter_sections_jsonl(
    inp: str, from_: int | None, to: int | None
) -> Iterable[Section]:
    """Always ask jq for JSONL objects: {section_index, abs_start, abs_end, full_text}
    Then parse into dataclass.
    """
    sel = build_selector(from_, to)
    jq_filter = f"{sel} | {{section_index, abs_start, abs_end, full_text}}"

    res = run_command(
        jq_cmd(inp, jq_filter, raw=False),  # -c (compact JSON per line)
        check=True,
        logger=LOGGER,
    )

    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        yield Section(
            section_index=int(obj["section_index"]),
            abs_start=str(obj["abs_start"]),
            abs_end=str(obj["abs_end"]),
            full_text=str(obj.get("full_text") or ""),
        )


def render_text(sections: Iterable[Section]) -> str:
    return (
        "\n".join(f"from {s.abs_start} to {s.abs_end}: {s.full_text}" for s in sections)
        + "\n"
    )


def render_tsv(sections: Iterable[Section]) -> str:
    # Match your jq tsv output exactly (tab-separated)
    return "".join(
        f"{s.section_index}\t{s.abs_start} -> {s.abs_end}\t{s.full_text}\n"
        for s in sections
    )


def render_jsonl(sections: Iterable[Section]) -> str:
    # Match jq -c behavior (compact JSON per line)
    lines = []
    for s in sections:
        lines.append(json.dumps(asdict(s), ensure_ascii=False, separators=(",", ":")))
    return "\n".join(lines) + ("\n" if lines else "")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract sections from transcript.json via jq JSONL, then format in Python."
    )
    ap.add_argument(
        "-i",
        "--in",
        dest="inp",
        required=True,
        help="Input JSON (e.g., transcripts.json)",
    )
    ap.add_argument(
        "-f",
        "--format",
        choices=["text", "tsv", "jsonl"],
        required=True,
        help="Output format",
    )
    ap.add_argument(
        "--from",
        dest="from_",
        type=int,
        default=None,
        help="inclusive lower bound for section_index",
    )
    ap.add_argument(
        "--to",
        dest="to",
        type=int,
        default=None,
        help="exclusive upper bound for section_index",
    )
    ap.add_argument(
        "--no-check",
        action="store_true",
        help="Do not raise on non-zero exit code (best-effort)",
    )
    args = ap.parse_args()

    # If you want --no-check to apply, you can wrap iter_sections_jsonl with try/except,
    # but run_command itself raises when check=True. We'll honor args.no_check here:
    try:
        sections = list(iter_sections_jsonl(args.inp, args.from_, args.to))
    except Exception:
        if args.no_check:
            return 0
        raise

    if args.format == "text":
        out = render_text(sections)
    elif args.format == "tsv":
        out = render_tsv(sections)
    else:
        out = render_jsonl(sections)

    print(out, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
