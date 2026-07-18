from collections.abc import Callable, Iterable, Iterator
from pathlib import Path


def iter_files(
    folder: Path,
    *,
    extensions: Iterable[str] | None = None,
    recursive: bool = True,
    predicate: Callable[[Path], bool] | None = None,
) -> Iterator[Path]:
    """Lazily iterate files in a folder with optional filtering.

    Args:
        folder: Root directory
        extensions: ("pptx", ".pdf"), None = all
        recursive: Whether to recurse
        predicate: Optional Path -> bool filter
    """
    if not folder.is_dir():
        raise NotADirectoryError(folder)

    iterator = folder.rglob("*") if recursive else folder.glob("*")

    ext_set = {f".{e.lower().lstrip('.')}" for e in extensions} if extensions else None

    for path in iterator:
        if not path.is_file():
            continue

        if ext_set and path.suffix.lower() not in ext_set:
            continue

        if predicate and not predicate(path):
            continue

        yield path
