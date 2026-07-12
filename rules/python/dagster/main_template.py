import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
# This generated main.py lives at <repo_root>/python/<this_package>/<file>.py
# in the runfiles tree, so two levels up is the repo root.
REPO_ROOT = PROJECT_ROOT.parents[1]
SITECUSTOMIZE_DIR = REPO_ROOT / "rules" / "python" / "dagster"

if __name__ == "__main__":
    asset_path = PROJECT_ROOT / "__DEFS_SRC__"

    # sitecustomize.py (auto-imported by Python at startup when its directory
    # is on PYTHONPATH) works around dagster-io/dagster#33851 so the webserver
    # UI's static assets don't 404 under Bazel's symlinked runfiles tree.
    # Shared at //rules/python/dagster:sitecustomize.py -- see that file.
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(SITECUSTOMIZE_DIR)
        if not existing_pythonpath
        else f"{SITECUSTOMIZE_DIR}{os.pathsep}{existing_pythonpath}"
    )

    subprocess.run(
        [sys.executable, "-m", "dagster", "dev", "-f", str(asset_path)] + sys.argv[1:],
        env=env,
    )
