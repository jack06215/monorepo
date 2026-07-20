#!/usr/bin/env python3
"""Render a Jira issue JSON (from acli) into readable terminal output."""

import json
import sys
from typing import Any

import pydantic


class Args(pydantic.BaseModel):
    """Command line arguments."""


def render_text_node(node: dict[str, Any]) -> str:
    """Render a text node, applying marks (code, strong, link)."""
    text = node.get("text", "")
    marks = node.get("marks", [])
    for mark in marks:
        t = mark.get("type")
        if t == "code":
            text = f"`{text}`"
        elif t == "strong":
            text = f"**{text}**"
        elif t == "em":
            text = f"_{text}_"
        elif t == "link":
            href = mark.get("attrs", {}).get("href", "")
            text = f"{text} ({href})" if href != text else text
    return text


def render_inline(content: list[dict[str, Any]]) -> str:
    """Concatenate inline text nodes."""
    return "".join(render_text_node(n) for n in (content or []))


def render_node(node: dict[str, Any], indent: int = 0) -> str:
    """Recursively render an ADF node to plain text."""
    t = node.get("type", "")
    content = node.get("content") or []
    pad = "  " * indent

    if t == "text":
        return render_text_node(node)

    elif t == "paragraph":
        inner = render_inline(content)
        return f"{pad}{inner}" if inner.strip() else ""

    elif t == "heading":
        level = node.get("attrs", {}).get("level", 1)
        inner = render_inline(content)
        prefix = "#" * level
        return f"\n{pad}{prefix} {inner}"

    elif t == "bulletList":
        items = []
        for item in content:
            body = "\n".join(
                render_node(child, indent + 1)
                for child in (item.get("content") or [])
                if render_node(child, indent + 1).strip()
            )
            items.append(f"{pad}• {body.strip()}")
        return "\n".join(items)

    elif t == "orderedList":
        items = []
        for i, item in enumerate(content, 1):
            body = "\n".join(
                render_node(child, indent + 1)
                for child in (item.get("content") or [])
                if render_node(child, indent + 1).strip()
            )
            items.append(f"{pad}{i}. {body.strip()}")
        return "\n".join(items)

    elif t == "codeBlock":
        code = "".join(n.get("text", "") for n in content)
        return f"{pad}```\n{code}\n{pad}```"

    elif t == "blockCard":
        url = node.get("attrs", {}).get("url", "")
        return f"{pad}{url}"

    elif t == "table":
        return render_table(node, indent)

    elif t in ("doc", "listItem"):
        lines = []
        for child in content:
            rendered = render_node(child, indent)
            if rendered.strip():
                lines.append(rendered)
        return "\n".join(lines)

    else:
        # Fallback: recurse into content
        lines = []
        for child in content:
            rendered = render_node(child, indent)
            if rendered.strip():
                lines.append(rendered)
        return "\n".join(lines)


def render_table(node: dict[str, Any], indent: int = 0) -> str:
    """Render an ADF table as aligned ASCII columns."""
    rows_data = []
    for row in node.get("content") or []:
        cells = []
        for cell in row.get("content") or []:
            cell_text = " ".join(
                render_node(child).strip()
                for child in (cell.get("content") or [])
                if render_node(child).strip()
            )
            cells.append(cell_text)
        rows_data.append(cells)

    if not rows_data:
        return ""

    col_count = max(len(r) for r in rows_data)
    col_widths = [0] * col_count
    for row in rows_data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    pad = "  " * indent
    sep = pad + "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    lines = [sep]
    for ri, row in enumerate(rows_data):
        cells_fmt = []
        for i in range(col_count):
            cell = row[i] if i < len(row) else ""
            cells_fmt.append(f" {cell:<{col_widths[i]}} ")
        lines.append(pad + "|" + "|".join(cells_fmt) + "|")
        if ri == 0:  # separator after header
            lines.append(sep)
    lines.append(sep)
    return "\n".join(lines)


def render_doc(doc: dict[str, Any] | None) -> str:
    if not doc:
        return "(empty)"
    content = doc.get("content") or []
    parts = []
    for node in content:
        rendered = render_node(node)
        if rendered.strip():
            parts.append(rendered)
    return "\n".join(parts).strip()


def format_datetime(s: str) -> str:
    """Convert ISO datetime to readable JST string."""
    if not s:
        return ""
    # e.g. "2026-06-18T10:28:11.681+0900" → "2026-06-18 10:28 JST"
    try:
        date, rest = s[:10], s[11:16]
        return f"{date} {rest} JST"
    except Exception:
        return s


def main(_args: Args) -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", file=sys.stderr)
        sys.exit(1)

    fields = data.get("fields", {})

    assignee = fields.get("assignee") or {}
    status = fields.get("status", {})
    comment_data = fields.get("comment") or {}
    comments = comment_data.get("comments") or []

    print("=" * 70)
    print(f"  {data.get('key')}  {fields.get('summary', '')}")
    print("=" * 70)
    print(f"  Status   : {status.get('statusCategory', {}).get('name', '')}")
    print(
        f"  Assignee : {assignee.get('displayName', 'Unassigned')} <{assignee.get('emailAddress', '')}>"
    )
    print()

    print("─" * 70)
    print("DESCRIPTION")
    print("─" * 70)
    desc = render_doc(fields.get("description"))
    print(desc if desc.strip() else "(no description)")
    print()

    print("─" * 70)
    print(f"COMMENTS ({len(comments)})")
    print("─" * 70)

    if not comments:
        print("(no comments)")
    else:
        for i, comment in enumerate(comments, 1):
            author = comment.get("author", {}).get("displayName", "Unknown")
            created = format_datetime(comment.get("created", ""))
            print(f"\n[{i}] {author}  ·  {created}")
            print("·" * 50)
            body = render_doc(comment.get("body"))
            print(body if body.strip() else "(empty)")

    print()
