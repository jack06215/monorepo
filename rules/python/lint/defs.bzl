"""Drop-in py_library / py_binary that also generate `<name>.lint` and `<name>.fix` targets.

`<name>.lint` (sh_test) runs `ruff check` + `mypy` over the target's srcs,
read-only. Run it with `bazel test //pkg:name.lint`.

`<name>.fix` (sh_binary) runs `ruff check --fix` + `ruff format` over the
target's srcs in place, editing the real files in the workspace rather than
the sandboxed copies. It must be invoked with `bazel run //pkg:name.fix`.
"""

load("@rules_python//python:py_binary.bzl", native_py_binary = "py_binary")
load("@rules_python//python:py_library.bzl", native_py_library = "py_library")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")

def _canon(label_str):
    return str(native.package_relative_label(label_str))

def _same_package_dep_srcs(deps, srcs_canon):
    # mypy needs sibling first-party modules on disk to resolve imports like
    # `from pkg import definition`, even though this target only *checks* its
    # own srcs. Pull those files in as extra sandbox data (not as extra
    # `.lint` args) for same-package `:label` deps declared earlier in this
    # BUILD file.
    extra = []
    for dep in deps:
        if not dep.startswith(":"):
            continue
        rule = native.existing_rule(dep[1:])
        if rule == None:
            continue
        for src in rule.get("srcs", []):
            if _canon(src) not in srcs_canon:
                extra.append(src)
    return extra

def _lint_and_fix_targets(name, srcs, deps = []):
    if not srcs:
        return

    srcs_canon = [_canon(s) for s in srcs]

    # mypy needs the target's own third-party deps (langchain-core, pydantic,
    # etc.) importable, or it silently treats them as Any and can misreport
    # errors (e.g. bogus overload-cannot-match / type-var findings). The
    # shared //rules/python/lint:mypy binary only carries mypy's own deps, so
    # build a copy of the console script wired to this target's deps instead.
    mypy_bin = name + ".mypy_bin"
    py_console_script_binary(
        name = mypy_bin,
        pkg = "@monorepo_pip//mypy",
        script = "mypy",
        deps = deps,
        legacy_create_init = False,
        visibility = ["//visibility:private"],
    )

    sh_test(
        name = name + ".lint",
        srcs = ["//rules/python/lint:lint.sh"],
        args = [
            "$(rootpath //rules/python/lint:ruff)",
            "$(rootpath :%s)" % mypy_bin,
        ] + ["$(rootpath %s)" % src for src in srcs],
        data = srcs + _same_package_dep_srcs(deps, srcs_canon) + [
            "//rules/python/lint:ruff",
            ":" + mypy_bin,
        ],
    )

    sh_binary(
        name = name + ".fix",
        srcs = ["//rules/python/lint:fix.sh"],
        args = [
            "$(rootpath //rules/python/lint:ruff)",
            native.package_name(),
        ] + srcs,
        data = srcs + ["//rules/python/lint:ruff"],
    )

def py_library(name, srcs = [], deps = [], **kwargs):
    native_py_library(name = name, srcs = srcs, deps = deps, **kwargs)
    _lint_and_fix_targets(name, srcs, deps)

def py_binary(name, srcs = [], deps = [], **kwargs):
    native_py_binary(name = name, srcs = srcs, deps = deps, **kwargs)
    _lint_and_fix_targets(name, srcs, deps)
