#!/usr/bin/env python3
# Normalize Kibana Dev Tools console output into valid JSON.
#
# Kibana renders strings containing quotes or newlines as triple-quoted
# "long string" blocks, which are not valid JSON and choke jq. This rewrites
# them into properly escaped JSON strings and passes everything else through
# untouched.
#
# Usage:  pbpaste | kibana_json_stringify.py | jq '...'
#         kibana_json_stringify.py < response.json | jq '...'

import json
import re
import sys

import pydantic


class Args(pydantic.BaseModel):
    """Command line arguments."""

# Matches a Kibana triple-quoted long-string: three double-quotes, any content
# (including newlines, via DOTALL), then three double-quotes. Non-greedy so
# balanced delimiter pairs match correctly.
LONG_STRING = re.compile(r'"""(.*?)"""', re.DOTALL)


def normalize(raw: str) -> str:
    # Rewrite each triple-quoted long-string into a valid escaped JSON string.
    # json.dumps handles all escaping (backslash, quote, newline, tab, unicode)
    # in the correct order.
    #
    # Caveat: assumes no snippet's actual text contains a literal triple-quote
    # sequence. Kibana only emits it as its own delimiter, so this holds for
    # console output.
    return LONG_STRING.sub(lambda m: json.dumps(m.group(1)), raw)


def context(text: str, pos: int, span: int = 60) -> str:
    # Caret-marked window around the failure position. Clips to a single line
    # so a compact one-line document stays readable.
    line_start = text.rfind("\n", 0, pos) + 1
    line_end = text.find("\n", pos)
    if line_end == -1:
        line_end = len(text)

    lo = max(line_start, pos - span)
    hi = min(line_end, pos + span)
    prefix = "..." if lo > line_start else ""
    pad = len(prefix) + (pos - lo)
    return f"{prefix}{text[lo:hi]}\n{' ' * pad}^"


def main(_args: Args) -> None:
    raw = sys.stdin.read().lstrip("\ufeff")  # drop a leading BOM if present
    out = normalize(raw)

    # Fail closed: on invalid JSON, report precisely on stderr and emit NOTHING
    # on stdout, so a downstream jq doesn't run on broken input and bury this
    # message under its own cryptic parse error.
    try:
        json.loads(out)
    except json.JSONDecodeError as e:
        print(
            f"kibana_json_stringify: invalid JSON at line {e.lineno}, "
            f"column {e.colno} (char {e.pos}): {e.msg}",
            file=sys.stderr,
        )
        print(context(out, e.pos), file=sys.stderr)
        sys.exit(1)

    sys.stdout.write(out)
