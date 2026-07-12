"""py_dagster: a py_binary macro for `dagster dev` targets.

Generates a launcher main.py that runs `dagster dev -f <defs_src>` as a
subprocess with //rules/python/dagster:sitecustomize.py on its PYTHONPATH --
working around dagster-io/dagster#33851 (Starlette's StaticFiles rejects the
symlinks in Bazel's runfiles tree, so the webserver UI's static assets 404
and the page loads blank). See sitecustomize.py for the patch itself.

Delete this indirection (and go back to a plain py_binary) once
dagster-webserver ships past the release containing that fix.
"""

load("@bazel_skylib//rules:expand_template.bzl", "expand_template")
load("@monorepo_pip//:requirements.bzl", "requirement")
load("//rules/python/lint:defs.bzl", "py_binary")

def dagster_dagit(name, defs_src, deps = [], data = [], **kwargs):
    """A py_binary that launches `dagster dev -f <defs_src>`."""
    main_out = name + "_main.py"

    expand_template(
        name = name + "_gen_main",
        template = "//rules/python/dagster:main_template.py",
        out = main_out,
        substitutions = {
            "__DEFS_SRC__": defs_src,
        },
    )

    py_binary(
        name = name,
        srcs = [main_out],
        main = main_out,
        data = data + ["//rules/python/dagster:sitecustomize.py"],
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
