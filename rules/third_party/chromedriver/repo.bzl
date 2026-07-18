"""Fetches a pinned ChromeDriver binary for the host platform from Chrome for Testing.

Usage from MODULE.bazel:

    chromedriver = use_extension("//rules/third_party/chromedriver:repo.bzl", "chromedriver_extension")
    use_repo(chromedriver, "chromedriver")

Then depend on `@chromedriver//:chromedriver` (a single-file filegroup).
"""

_VERSION = "150.0.7871.124"

# https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json
# The manifest doesn't publish sha256, so these were computed by downloading
# each archive and running `shasum -a 256` over it.
#
# ChromeDriver only supports the matching Chrome major version (see
# https://developer.chrome.com/docs/chromedriver#version), so this pin must
# track whatever Chrome major version is installed locally -- bump it (and
# the sha256s below) if `bazel run` starts failing with a
# "SessionNotCreatedException: ... only supports Chrome version N" error.
_PLATFORMS = {
    "mac-arm64": struct(
        os = "mac os x",
        cpu = "aarch64",
        sha256 = "ac7129faa67c481916ade9801538183af1f88da9f141a00b9651d472771c339e",
    ),
    "mac-x64": struct(
        os = "mac os x",
        cpu = "x86_64",
        sha256 = "4523b5ed1f69f6347ddac411ff5c669964be692f64be0e651554d8335120f12f",
    ),
    "linux64": struct(
        os = "linux",
        cpu = "x86_64",
        sha256 = "a02216d56e594eecaa3d324de65517d130171c2ca09514320519c820cf400ae0",
    ),
}

def _host_platform(repository_ctx):
    os_name = repository_ctx.os.name.lower()
    cpu = repository_ctx.os.arch
    for platform, info in _PLATFORMS.items():
        if info.os == os_name and info.cpu == cpu:
            return platform
    fail("chromedriver: unsupported host platform ({}, {}); supported: {}".format(
        os_name,
        cpu,
        ", ".join(_PLATFORMS.keys()),
    ))

def _chromedriver_repository_impl(repository_ctx):
    platform = _host_platform(repository_ctx)
    info = _PLATFORMS[platform]
    binary = "chromedriver-{}/chromedriver".format(platform)

    repository_ctx.download_and_extract(
        url = "https://storage.googleapis.com/chrome-for-testing-public/{version}/{platform}/chromedriver-{platform}.zip".format(
            version = _VERSION,
            platform = platform,
        ),
        sha256 = info.sha256,
    )

    # The zip's executable bit isn't always preserved on extraction.
    result = repository_ctx.execute(["chmod", "+x", binary])
    if result.return_code != 0:
        fail("chromedriver: chmod +x failed: {}".format(result.stderr))

    repository_ctx.file(
        "BUILD.bazel",
        content = """\
filegroup(
    name = "chromedriver",
    srcs = ["{binary}"],
    visibility = ["//visibility:public"],
)
""".format(binary = binary),
    )

chromedriver_repository = repository_rule(
    implementation = _chromedriver_repository_impl,
    doc = "Downloads the pinned ChromeDriver release for the host OS/CPU.",
)

def _chromedriver_extension_impl(_module_ctx):
    chromedriver_repository(name = "chromedriver")

chromedriver_extension = module_extension(
    implementation = _chromedriver_extension_impl,
    doc = "Registers @chromedriver, a single-file filegroup with the host-platform chromedriver binary.",
)
