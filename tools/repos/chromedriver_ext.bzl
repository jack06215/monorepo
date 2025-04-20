
""""""
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@bazel_tools//tools/build_defs/repo:attrs.bzl", "attr")
load("@bazel_tools//tools/build_defs/repo:repository.bzl", "module_extension")

def _impl(ctx):
    # these attrs come from MODULE.bazel below
    version = ctx.attr.version
    sha256  = ctx.attr.sha256
    http_archive(
        name         = ctx.name,  # e.g. "chromedriver_win32"
        urls         = ["https://chromedriver.storage.googleapis.com/%s/chromedriver_win32.zip" % version],
        sha256       = sha256,
        strip_prefix = "", 
    )

chromedriver_extension = module_extension(
    implementation = _impl,
    attrs = {
        "version": attr.string(mandatory = True),
        "sha256":  attr.string(mandatory = True),
    },
)
