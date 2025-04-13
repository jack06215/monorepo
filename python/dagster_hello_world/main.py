import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

if __name__ == "__main__":
    asset_path = PROJECT_ROOT / "assets.py"
    subprocess.run(
        ["dagster", "dev", "-f", str(asset_path)] + sys.argv[1:],
    )
