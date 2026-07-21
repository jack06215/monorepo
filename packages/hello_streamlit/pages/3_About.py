import os

import streamlit as st

from packages.hello_streamlit.shared import APP_NAME

st.title("ℹ️ About")
st.markdown(
    f"**{APP_NAME}** is a Bazel-built multi-page Streamlit app.\n\n"
    "- Entry point: `main.py` — passed as `app` to `streamlit_app`\n"
    "- Pages: `pages/*.py` — bundled via `data = glob([...])`\n"
    "- Shared code: `shared.py` — a `py_library` dep\n"
    "- Third-party deps (e.g. pandas) — passed via `deps`\n"
    "- Env vars: set via the `env` attribute — see below\n"
    "- Launched with `bazel run //packages/hello_streamlit`, which shells out "
    "to `streamlit run main.py`"
)

st.subheader("Reading an env var")
app_env = os.getenv("APP_ENV", "<unset>")
st.write("Live value from `os.getenv(\"APP_ENV\")`:")
st.code(app_env, language="text")
st.markdown(
    "It's injected by the `env` attribute on the target, which rides through "
    "`bazel run` into the app's environment:"
)
st.code(
    'streamlit_app(\n'
    '    name = "hello_streamlit",\n'
    '    app = "main.py",\n'
    '    env = {"APP_ENV": "demo"},  # -> os.getenv("APP_ENV")\n'
    '    ...\n'
    ')',
    language="python",
)
st.caption(
    "The `env` attr value is static and takes precedence over `--run_env` and "
    "shell exports. To inject a value at run time instead (e.g. secrets), leave "
    "the var out of `env` and use "
    "`bazel run --run_env=APP_ENV=prod //packages/hello_streamlit` or export it "
    "in your shell. `--action_env` is build-only and never reaches "
    "`os.getenv()`."
)
