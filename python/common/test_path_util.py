import tempfile
import unittest
from pathlib import Path

from common.path_util import iter_files


class IterFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

        (self.root / "a.txt").write_text("a")
        (self.root / "b.PDF").write_text("b")
        (self.root / "c.md").write_text("c")

        nested = self.root / "nested"
        nested.mkdir()
        (nested / "d.txt").write_text("d")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_raises_when_folder_missing(self) -> None:
        with self.assertRaises(NotADirectoryError):
            list(iter_files(self.root / "does_not_exist"))

    def test_raises_when_folder_is_a_file(self) -> None:
        with self.assertRaises(NotADirectoryError):
            list(iter_files(self.root / "a.txt"))

    def test_recursive_by_default_returns_all_files(self) -> None:
        found = {p.name for p in iter_files(self.root)}
        self.assertEqual(found, {"a.txt", "b.PDF", "c.md", "d.txt"})

    def test_non_recursive_skips_nested_files(self) -> None:
        found = {p.name for p in iter_files(self.root, recursive=False)}
        self.assertEqual(found, {"a.txt", "b.PDF", "c.md"})

    def test_extension_filter_is_case_insensitive_and_dot_agnostic(self) -> None:
        found = {p.name for p in iter_files(self.root, extensions=["TXT"])}
        self.assertEqual(found, {"a.txt", "d.txt"})

        found_with_dot = {p.name for p in iter_files(self.root, extensions=[".txt"])}
        self.assertEqual(found_with_dot, {"a.txt", "d.txt"})

    def test_predicate_filters_files(self) -> None:
        found = {
            p.name
            for p in iter_files(self.root, predicate=lambda p: p.name.startswith("a"))
        }
        self.assertEqual(found, {"a.txt"})

    def test_extensions_and_predicate_combine(self) -> None:
        found = {
            p.name
            for p in iter_files(
                self.root,
                extensions=["txt"],
                predicate=lambda p: "nested" not in p.parts,
            )
        }
        self.assertEqual(found, {"a.txt"})


if __name__ == "__main__":
    unittest.main()
