"""py_dagster: a py_binary macro for `dagster dev` targets.

Generates a launcher main.py that runs `dagster dev -f <defs_src>` as a
subprocess with //rules/python/dagster:sitecustomize.py on its PYTHONPATH --
working around dagster-io/dagster#33851 (Starlette's StaticFiles rejects the
symlinks in Bazel's runfiles tree, so the webserver UI's static assets 404
and the page loads blank). See sitecustomize.py for the patch itself.

Delete this indirection (and go back to a plain py_binary) once
dagster-webserver ships past the release containing that fix.
"""

load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@monorepo_pip//:requirements.bzl", "requirement")
load("//rules/python/lint:defs.bzl", "py_binary")

_MAIN_TEMPLATE = """\
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
    asset_path = PROJECT_ROOT / "{defs_src}"

    # sitecustomize.py (auto-imported by Python at startup when its directory
    # is on PYTHONPATH) works around dagster-io/dagster#33851 so the webserver
    # UI's static assets don't 404 under Bazel's symlinked runfiles tree.
    # Shared at //rules/python/dagster:sitecustomize.py -- see that file.
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(SITECUSTOMIZE_DIR)
        if not existing_pythonpath
        else f"{{SITECUSTOMIZE_DIR}}{{os.pathsep}}{{existing_pythonpath}}"
    )

    subprocess.run(
        [sys.executable, "-m", "dagster", "dev", "-f", str(asset_path)] + sys.argv[1:],
        env=env,
    )
"""

def dagster_dagit(name, defs_src, deps = [], data = [], **kwargs):
    """A py_binary that launches `dagster dev -f <defs_src>`."""
    main_out = name + "_main.py"

    write_file(
        name = name + "_gen_main",
        out = main_out,
        content = _MAIN_TEMPLATE.format(defs_src = defs_src).splitlines(),
    )

    py_binary(
        name = name,
        srcs = [main_out],
        main = main_out,
        deps = deps + [
            requirement("dagster"),
            requirement("dagster-webserver"),
            # uvicorn (used by dagster-webserver) needs a WebSocket
            # implementation for GraphQL subscriptions (live UI updates), or
            # it logs "Unsupported upgrade request" for every WS connection.
            requirement("websockets"),
        ],
        **kwargs
    )
