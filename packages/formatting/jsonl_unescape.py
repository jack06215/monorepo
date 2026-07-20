#!/usr/bin/env python3
"""Convert a JSONL file with into human-readable UTF-8 JSONL, written to stdout.

Usage:
    python jsonl_unescape.py input.jsonl | pbcopy
    python jsonl_unescape.py input.jsonl > output.jsonl
    cat input.jsonl | python jsonl_unescape.py | pbcopy

Add --pretty to indent each JSON object instead of keeping it on one line.
"""

import contextlib
import json
import sys
from typing import IO, Generator

import pydantic


class Args(pydantic.BaseModel):
    """Command line arguments."""

    input: str | None = None
    pretty: bool = False


@contextlib.contextmanager
def _open_input(path: str | None) -> Generator[IO[str]]:
    if path is None:
        yield sys.stdin
        return
    with open(path, "r", encoding="utf-8") as fp:
        yield fp


def main(args: Args) -> None:
    indent = 2 if args.pretty else None

    with _open_input(args.input) as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                print(f"Line {line_number}: invalid JSON ({exc})", file=sys.stderr)
                continue
            sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=indent))
            sys.stdout.write("\n")
