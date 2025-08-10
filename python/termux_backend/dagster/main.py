import subprocess
import sys

from python.termux_backend.dagster import workspace_definition

if __name__ == "__main__":
    asset_path = workspace_definition.PROJECT_ROOT / "workspace.py"
    subprocess.run(
        ["dagster", "dev", "-f", asset_path.as_posix()] + sys.argv[1:],
    )
