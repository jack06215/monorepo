import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from formatting.jsonl_unescape import Args, main


class MainTest(unittest.TestCase):
    def _run(self, args: Args, stdin_text: str = "") -> tuple[str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with patch("sys.stdin", io.StringIO(stdin_text)):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                main(args)
        return out.getvalue(), err.getvalue()

    def test_reads_from_stdin_by_default(self) -> None:
        out, err = self._run(Args(), '{"a": 1}\n')
        self.assertEqual(out, '{"a": 1}\n')
        self.assertEqual(err, "")

    def test_skips_blank_lines(self) -> None:
        out, _ = self._run(Args(), '{"a": 1}\n\n   \n{"b": 2}\n')
        self.assertEqual(out, '{"a": 1}\n{"b": 2}\n')

    def test_invalid_json_line_reports_error_and_continues(self) -> None:
        out, err = self._run(Args(), 'not json\n{"a": 1}\n')
        self.assertEqual(out, '{"a": 1}\n')
        self.assertIn("Line 1: invalid JSON", err)

    def test_preserves_non_ascii_characters(self) -> None:
        out, _ = self._run(
            Args(), '{"greeting": "\\u3053\\u3093\\u306b\\u3061\\u306f"}\n'
        )
        self.assertEqual(out, '{"greeting": "こんにちは"}\n')

    def test_pretty_indents_output(self) -> None:
        out, _ = self._run(Args(pretty=True), '{"a": 1, "b": 2}\n')
        self.assertEqual(out, '{\n  "a": 1,\n  "b": 2\n}\n')

    def test_reads_from_file_when_input_path_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.jsonl"
            path.write_text('{"x": 1}\n{"y": 2}\n', encoding="utf-8")
            out, _ = self._run(Args(input=str(path)))
        self.assertEqual(out, '{"x": 1}\n{"y": 2}\n')


if __name__ == "__main__":
    unittest.main()
