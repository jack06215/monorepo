"""Drop-in cc_test / cc_library that also generate `<name>.check` and
`<name>.fix` targets.

`<name>.check` (sh_test) runs `clang-format --dry-run --Werror` + `clang-tidy`
over the target's srcs, read-only. Run with `bazel test //pkg:name.check`.

`<name>.fix` (sh_binary) runs `clang-format -i` over the target's srcs in
place, editing the real files in the workspace rather than the sandboxed
copies. Must be invoked with `bazel run //pkg:name.fix`.

Wraps whatever clang-format/clang-tidy is found on PATH (or a common
Homebrew keg-only llvm install) -- not hermetic, requires them installed
locally (e.g. `brew install clang-format llvm`).

Use these only for code you own. Vendored third-party headers (e.g.
catch.hpp, prettyprint.hpp) should stay on the plain native cc_library --
wrapping them here would reformat/lint code that isn't ours to change.
"""

load("@rules_cc//cc:defs.bzl", native_cc_library = "cc_library", native_cc_test = "cc_test")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")

def _canon(label_str):
    return str(native.package_relative_label(label_str))

def _same_package_dep_srcs(deps, srcs_canon):
    # clang-tidy needs the headers a .cpp #includes (e.g. the vendored
    # catch.hpp/prettyprint.hpp cc_library wrappers) physically present to
    # resolve the #include chain, even though this target only *checks* its
    # own srcs. Pull those files in as extra sandbox data for same-package
    # `:label` deps declared earlier in this BUILD file.
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

def _check_and_fix_targets(name, srcs, deps = []):
    if not srcs:
        return

    srcs_canon = [_canon(s) for s in srcs]

    sh_test(
        name = name + ".check",
        srcs = ["//rules/cpp/lint:check.sh"],
        args = ["$(rootpath %s)" % src for src in srcs],
        data = srcs + _same_package_dep_srcs(deps, srcs_canon),
        # Shells out to a system clang-format/clang-tidy install, which
        # isn't a declared Bazel dependency. The "cpp_lint" tag lets
        # check_all.sh/fix_all.sh find exactly these targets via `bazel
        # query`, since python's lint macro also produces `.fix`-suffixed
        # targets and a bare name-suffix query would sweep those in too.
        tags = ["cpp_lint", "no-sandbox"],
    )

    sh_binary(
        name = name + ".fix",
        srcs = ["//rules/cpp/lint:fix.sh"],
        args = [native.package_name()] + srcs,
        data = srcs,
        tags = ["cpp_lint"],
    )

def cc_test(name, srcs = [], deps = [], **kwargs):
    native_cc_test(name = name, srcs = srcs, deps = deps, **kwargs)
    _check_and_fix_targets(name, srcs, deps)

def cc_library(name, srcs = [], deps = [], **kwargs):
    native_cc_library(name = name, srcs = srcs, deps = deps, **kwargs)
    _check_and_fix_targets(name, srcs, deps)
