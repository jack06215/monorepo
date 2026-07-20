import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import Any
from unittest.mock import patch

from formatting.jira_ticket import (
    Args,
    format_datetime,
    main,
    render_doc,
    render_inline,
    render_node,
    render_table,
    render_text_node,
)


class RenderTextNodeTest(unittest.TestCase):
    def test_plain_text_without_marks(self) -> None:
        self.assertEqual(render_text_node({"text": "hello"}), "hello")

    def test_missing_text_key_defaults_to_empty(self) -> None:
        self.assertEqual(render_text_node({}), "")

    def test_code_mark(self) -> None:
        self.assertEqual(
            render_text_node({"text": "x", "marks": [{"type": "code"}]}), "`x`"
        )

    def test_strong_mark(self) -> None:
        self.assertEqual(
            render_text_node({"text": "x", "marks": [{"type": "strong"}]}), "**x**"
        )

    def test_em_mark(self) -> None:
        self.assertEqual(
            render_text_node({"text": "x", "marks": [{"type": "em"}]}), "_x_"
        )

    def test_link_mark_appends_href_when_different_from_text(self) -> None:
        node = {
            "text": "click here",
            "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}],
        }
        self.assertEqual(render_text_node(node), "click here (https://example.com)")

    def test_link_mark_omits_href_when_same_as_text(self) -> None:
        node = {
            "text": "https://example.com",
            "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}],
        }
        self.assertEqual(render_text_node(node), "https://example.com")

    def test_multiple_marks_apply_in_order(self) -> None:
        node = {"text": "x", "marks": [{"type": "code"}, {"type": "strong"}]}
        self.assertEqual(render_text_node(node), "**`x`**")

    def test_unknown_mark_type_is_ignored(self) -> None:
        node = {"text": "x", "marks": [{"type": "underline"}]}
        self.assertEqual(render_text_node(node), "x")


class RenderInlineTest(unittest.TestCase):
    def test_concatenates_multiple_nodes(self) -> None:
        content = [{"text": "a"}, {"text": "b", "marks": [{"type": "strong"}]}]
        self.assertEqual(render_inline(content), "a**b**")

    def test_empty_list_returns_empty_string(self) -> None:
        self.assertEqual(render_inline([]), "")

    def test_none_returns_empty_string(self) -> None:
        self.assertEqual(render_inline(None), "")  # type: ignore[arg-type]


class RenderNodeTest(unittest.TestCase):
    def test_text_node(self) -> None:
        self.assertEqual(render_node({"type": "text", "text": "hi"}), "hi")

    def test_paragraph_renders_inline_content(self) -> None:
        node = {"type": "paragraph", "content": [{"type": "text", "text": "hi"}]}
        self.assertEqual(render_node(node), "hi")

    def test_empty_paragraph_renders_empty_string(self) -> None:
        node = {"type": "paragraph", "content": []}
        self.assertEqual(render_node(node), "")

    def test_paragraph_indented(self) -> None:
        node = {"type": "paragraph", "content": [{"type": "text", "text": "hi"}]}
        self.assertEqual(render_node(node, indent=1), "  hi")

    def test_heading_includes_level_prefix_and_leading_newline(self) -> None:
        node = {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Title"}],
        }
        self.assertEqual(render_node(node), "\n## Title")

    def test_heading_defaults_to_level_one(self) -> None:
        node = {"type": "heading", "content": [{"type": "text", "text": "Title"}]}
        self.assertEqual(render_node(node), "\n# Title")

    def test_bullet_list_renders_items_with_bullet_prefix(self) -> None:
        node = {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "one"}],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "two"}],
                        }
                    ],
                },
            ],
        }
        self.assertEqual(render_node(node), "• one\n• two")

    def test_ordered_list_numbers_items(self) -> None:
        node = {
            "type": "orderedList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "first"}],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "second"}],
                        }
                    ],
                },
            ],
        }
        self.assertEqual(render_node(node), "1. first\n2. second")

    def test_code_block_wraps_in_fence(self) -> None:
        node = {"type": "codeBlock", "content": [{"text": "print(1)"}]}
        self.assertEqual(render_node(node), "```\nprint(1)\n```")

    def test_block_card_renders_url(self) -> None:
        node = {"type": "blockCard", "attrs": {"url": "https://example.com"}}
        self.assertEqual(render_node(node), "https://example.com")

    def test_doc_joins_nonblank_children(self) -> None:
        node = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "a"}]},
                {"type": "paragraph", "content": []},
                {"type": "paragraph", "content": [{"type": "text", "text": "b"}]},
            ],
        }
        self.assertEqual(render_node(node), "a\nb")

    def test_unknown_type_falls_back_to_recursing_content(self) -> None:
        node = {
            "type": "panel",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "x"}]}
            ],
        }
        self.assertEqual(render_node(node), "x")

    def test_table_type_delegates_to_render_table(self) -> None:
        node = {
            "type": "table",
            "content": [
                {"content": [{"content": [{"type": "text", "text": "a"}]}]},
            ],
        }
        self.assertIn("a", render_node(node))


class RenderTableTest(unittest.TestCase):
    def test_empty_table_returns_empty_string(self) -> None:
        self.assertEqual(render_table({"content": []}), "")

    def test_aligns_columns_and_draws_separators(self) -> None:
        node = {
            "content": [
                {
                    "content": [
                        {"content": [{"type": "text", "text": "Name"}]},
                        {"content": [{"type": "text", "text": "Age"}]},
                    ]
                },
                {
                    "content": [
                        {"content": [{"type": "text", "text": "Bob"}]},
                        {"content": [{"type": "text", "text": "42"}]},
                    ]
                },
            ]
        }
        expected = (
            "+------+-----+\n"
            "| Name | Age |\n"
            "+------+-----+\n"
            "| Bob  | 42  |\n"
            "+------+-----+"
        )
        self.assertEqual(render_table(node), expected)

    def test_pads_missing_cells_in_ragged_rows(self) -> None:
        node = {
            "content": [
                {
                    "content": [
                        {"content": [{"type": "text", "text": "a"}]},
                        {"content": [{"type": "text", "text": "b"}]},
                    ]
                },
                {"content": [{"content": [{"type": "text", "text": "c"}]}]},
            ]
        }
        rendered = render_table(node)
        self.assertIn("| c |   |", rendered)


class RenderDocTest(unittest.TestCase):
    def test_none_returns_placeholder(self) -> None:
        self.assertEqual(render_doc(None), "(empty)")

    def test_empty_dict_returns_placeholder(self) -> None:
        self.assertEqual(render_doc({}), "(empty)")

    def test_joins_and_strips_rendered_parts(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "hello"}]}
            ],
        }
        self.assertEqual(render_doc(doc), "hello")

    def test_filters_out_blank_nodes(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": []},
                {"type": "paragraph", "content": [{"type": "text", "text": "hi"}]},
            ],
        }
        self.assertEqual(render_doc(doc), "hi")


class FormatDatetimeTest(unittest.TestCase):
    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual(format_datetime(""), "")

    def test_formats_iso_datetime_to_jst(self) -> None:
        self.assertEqual(
            format_datetime("2026-06-18T10:28:11.681+0900"), "2026-06-18 10:28 JST"
        )


class MainTest(unittest.TestCase):
    def _run_main(self, payload: dict) -> tuple[str, str, object]:
        out = io.StringIO()
        err = io.StringIO()
        code: object = None
        with patch("sys.stdin", io.StringIO(json.dumps(payload))):
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    main(Args())
                except SystemExit as e:
                    code = e.code
        return out.getvalue(), err.getvalue(), code

    def test_invalid_json_exits_with_error(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch("sys.stdin", io.StringIO("not json")):
            with redirect_stdout(out), redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    main(Args())
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("JSON parse error", err.getvalue())

    def test_renders_full_ticket(self) -> None:
        payload = {
            "key": "PROJ-1",
            "fields": {
                "summary": "Fix the bug",
                "status": {"statusCategory": {"name": "In Progress"}},
                "assignee": {
                    "displayName": "Jane Doe",
                    "emailAddress": "jane@example.com",
                },
                "description": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Body text"}],
                        }
                    ],
                },
                "comment": {
                    "comments": [
                        {
                            "author": {"displayName": "John"},
                            "created": "2026-06-18T10:28:11.681+0900",
                            "body": {
                                "type": "doc",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {"type": "text", "text": "A comment"}
                                        ],
                                    }
                                ],
                            },
                        }
                    ]
                },
            },
        }
        out, err, code = self._run_main(payload)
        self.assertIsNone(code)
        self.assertEqual(err, "")
        self.assertIn("PROJ-1", out)
        self.assertIn("Fix the bug", out)
        self.assertIn("In Progress", out)
        self.assertIn("Jane Doe <jane@example.com>", out)
        self.assertIn("Body text", out)
        self.assertIn("COMMENTS (1)", out)
        self.assertIn("John", out)
        self.assertIn("2026-06-18 10:28 JST", out)
        self.assertIn("A comment", out)

    def test_renders_defaults_for_missing_fields(self) -> None:
        payload: dict[str, Any] = {"fields": {}}
        out, _, code = self._run_main(payload)
        self.assertIsNone(code)
        self.assertIn("Unassigned", out)
        self.assertIn("(empty)", out)
        self.assertIn("(no comments)", out)


if __name__ == "__main__":
    unittest.main()
