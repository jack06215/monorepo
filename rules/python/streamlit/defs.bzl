"""streamlit_app: a py_binary macro for `streamlit run` targets.

Streamlit apps are started with `streamlit run <script>`, which boots the
Streamlit server and the script-rerun runtime that renders the UI. Running the
script directly with `python` renders nothing, and a plain py_binary only does
the latter -- so this macro generates a small launcher that shells out to
`streamlit run <app>` instead. It is the same indirection
//rules/python/dagster uses to wrap `dagster dev`.
"""

load("@bazel_skylib//rules:expand_template.bzl", "expand_template")
load("@monorepo_pip//:requirements.bzl", "requirement")
load("//rules/python/lint:defs.bzl", "py_binary")

def streamlit_app(name, app, deps = [], data = [], open_browser = True, **kwargs):
    """A py_binary that launches `streamlit run <app>`.

    Args:
        name: target name; run it with `bazel run //pkg:name`.
        app: the Streamlit app source file (e.g. "main.py"). Bundled into the
            binary's runfiles and passed to `streamlit run`.
        deps: extra deps for the app (first-party libs, third-party reqs).
        data: extra runtime data files.
        open_browser: if True (default), open the default browser once the
            server is up. Set False for headless server/CI targets.
        **kwargs: forwarded to the underlying py_binary.
    """
    main_out = name + "_main.py"

    expand_template(
        name = name + "_gen_main",
        template = "//rules/python/streamlit:main_template.py",
        out = main_out,
        substitutions = {
            "__APP_SRC__": app,
            "__OPEN_BROWSER__": "True" if open_browser else "False",
        },
    )

    py_binary(
        name = name,
        srcs = [main_out],
        main = main_out,
        data = data + [app],
        deps = deps + [
            requirement("streamlit"),
        ],
        **kwargs
    )
