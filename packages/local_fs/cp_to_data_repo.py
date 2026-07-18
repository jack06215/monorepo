import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal

SupportedDataType = Literal["teamspirit_working_time"]


def user_root() -> Path:
    return Path("/Users/jack.cho")


DATA_REPO_ROOT = user_root() / Path("workspace/data-repository")
DOWNLOAD_ROOT = user_root() / "Downloads"


@dataclass
class DataRepoBase:
    filename_pattern: ClassVar[str]
    name: ClassVar[str]

    @property
    def root_dir(self) -> Path:
        return DATA_REPO_ROOT / Path(self.name)


@dataclass
class TeamSpiritWorkingTimeDataRepo(DataRepoBase):
    filename_pattern = "teamspirit_working_time-*.json"
    name = "teamspirit_working_time"


SupprotedArgsType = TeamSpiritWorkingTimeDataRepo


def construct_args(type: str) -> SupprotedArgsType:
    if type == "teamspirit_working_time":
        return TeamSpiritWorkingTimeDataRepo()
    raise RuntimeError("Unsupported args type.")


def copy_files(filename_pattern: str, dst: Path):
    """Copy files from Downloads folder to a destination folder.

    Creates the folder if missing, and overwrites existing files.
    """
    dst.mkdir(parents=True, exist_ok=True)

    files = DOWNLOAD_ROOT.glob(filename_pattern)
    if not files:
        print(f"No files match pattern: {filename_pattern}")
        return

    for file_path in files:
        src_file = Path(file_path)
        dst_file = dst / src_file.name

        shutil.copy2(src_file, dst_file)

        print(f"Copied: {src_file} -> {dst_file}")

    print("Done.")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Move data to data repository.")
    arg_parser.add_argument("--type", required=True)
    args = construct_args(**vars(arg_parser.parse_args()))

    copy_files(
        filename_pattern=args.filename_pattern,
        dst=args.root_dir,
    )
