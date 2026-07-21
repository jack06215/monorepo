import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# Whether to open a browser once the server is up. The "__OPEN_BROWSER__"
# token is substituted with True/False by the streamlit_app macro
# (open_browser attr); it lives inside a string so this file stays valid,
# lintable Python before substitution.
OPEN_BROWSER = "__OPEN_BROWSER__" == "True"

DEFAULT_ADDRESS = "localhost"
DEFAULT_PORT = "8501"  # Streamlit's own default when --server.port is unset.


def _arg_value(args: list[str], key: str, default: str) -> str:
    """Read a `--key value` / `--key=value` flag out of forwarded argv."""
    prefix = key + "="
    for i, arg in enumerate(args):
        if arg.startswith(prefix):
            return arg[len(prefix):]
        if arg == key and i + 1 < len(args):
            return args[i + 1]
    return default


def _open_browser_when_ready(address: str, port: str) -> None:
    # Streamlit auto-opens a browser only in non-headless mode, which also
    # triggers a blocking first-run "Email:" prompt. We stay headless (see
    # below) and open the browser ourselves once the port accepts a
    # connection, so the page loads on the first try instead of erroring.
    host = "localhost" if address in ("0.0.0.0", "") else address
    for _ in range(150):  # ~30s at 0.2s/poll
        try:
            with socket.create_connection((host, int(port)), timeout=0.5):
                break
        except OSError:
            time.sleep(0.2)
    else:
        return
    webbrowser.open_new(f"http://{host}:{port}")


if __name__ == "__main__":
    app_path = PROJECT_ROOT / "__APP_SRC__"
    extra = sys.argv[1:]

    if OPEN_BROWSER:
        address = _arg_value(extra, "--server.address", DEFAULT_ADDRESS)
        port = _arg_value(extra, "--server.port", DEFAULT_PORT)
        threading.Thread(
            target=_open_browser_when_ready,
            args=(address, port),
            daemon=True,
        ).start()

    # Streamlit apps are started with `streamlit run <script>`, not by
    # executing the script directly: that command boots the Streamlit server
    # and the script-rerun runtime that renders the UI. A plain py_binary only
    # runs `python main.py`, which renders nothing, so this generated launcher
    # shells out to `streamlit run` instead -- the same indirection
    # //rules/python/dagster uses to wrap `dagster dev`.
    #
    # --server.headless=true keeps `bazel run` non-interactive: otherwise
    # Streamlit's first run blocks on an "Email:" prompt in the terminal. The
    # browser is opened above instead of by Streamlit itself.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "--server.headless=true",
            str(app_path),
        ]
        + extra,
    )
