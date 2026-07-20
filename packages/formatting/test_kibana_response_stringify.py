import contextlib
import io
import unittest
from unittest.mock import patch

from formatting.kibana_response_stringify import Args, context, main, normalize


class NormalizeTest(unittest.TestCase):
    def test_passes_through_input_without_long_strings(self) -> None:
        raw = '{"a": 1, "b": "plain"}'
        self.assertEqual(normalize(raw), raw)

    def test_rewrites_triple_quoted_long_string(self) -> None:
        raw = '{"query": """line one\nline "two"\nline three"""}'
        result = normalize(raw)
        self.assertEqual(result, '{"query": "line one\\nline \\"two\\"\\nline three"}')

    def test_rewrites_multiple_long_strings(self) -> None:
        raw = '{"a": """x\ny""", "b": """z"""}'
        result = normalize(raw)
        self.assertEqual(result, '{"a": "x\\ny", "b": "z"}')


class ContextTest(unittest.TestCase):
    def test_marks_position_with_caret(self) -> None:
        text = "abcdefgh"
        result = context(text, 3, span=10)
        self.assertEqual(result, "abcdefgh\n   ^")

    def test_prefixes_ellipsis_when_clipped_before_start(self) -> None:
        text = "x" * 100
        result = context(text, 80, span=10)
        lines = result.split("\n")
        self.assertTrue(lines[0].startswith("..."))
        caret_index = lines[1].index("^")
        self.assertEqual(lines[0][caret_index], text[80])

    def test_clips_to_single_line(self) -> None:
        text = "first line\nsecond line here\nthird"
        pos = text.index("second") + 3
        result = context(text, pos, span=100)
        self.assertNotIn("first line", result)
        self.assertNotIn("third", result)
        self.assertIn("second line here", result)

    def test_handles_position_on_last_line(self) -> None:
        text = "only one line no newline"
        pos = len(text) - 1
        result = context(text, pos, span=100)
        self.assertIn("only one line no newline", result)


class MainTest(unittest.TestCase):
    def _run(self, stdin_text: str) -> tuple[str, str, object]:
        out = io.StringIO()
        err = io.StringIO()
        code: object = None
        with patch("sys.stdin", io.StringIO(stdin_text)):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    main(Args())
                except SystemExit as e:
                    code = e.code
        return out.getvalue(), err.getvalue(), code

    def test_normalizes_and_writes_valid_json(self) -> None:
        out, err, code = self._run('{"msg": """hi\nthere"""}')
        self.assertIsNone(code)
        self.assertEqual(err, "")
        self.assertEqual(out, '{"msg": "hi\\nthere"}')

    def test_strips_leading_bom(self) -> None:
        out, _, code = self._run("\ufeff" + '{"a": 1}')
        self.assertIsNone(code)
        self.assertEqual(out, '{"a": 1}')

    def test_invalid_json_exits_nonzero_and_writes_nothing_to_stdout(self) -> None:
        out, err, code = self._run("{not valid json")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("invalid JSON", err)


if __name__ == "__main__":
    unittest.main()
