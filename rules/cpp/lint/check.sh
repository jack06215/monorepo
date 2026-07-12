#!/usr/bin/env bash
# Runs clang-format --dry-run --Werror + clang-tidy over a cc_test's srcs,
# read-only. Wraps whatever clang-format/clang-tidy is found on PATH (or a
# common Homebrew keg-only llvm install) -- not hermetic, requires them
# installed locally. Invoked as: check.sh <src>...
set -euo pipefail

find_tool() {
  local name="$1"
  if command -v "${name}" >/dev/null 2>&1; then
    command -v "${name}"
    return
  fi
  for prefix in /opt/homebrew/opt/llvm /usr/local/opt/llvm; do
    if [[ -x "${prefix}/bin/${name}" ]]; then
      echo "${prefix}/bin/${name}"
      return
    fi
  done
  echo "error: ${name} not found on PATH or common Homebrew keg-only locations (try: brew install llvm)" >&2
  exit 1
}

clang_format="$(find_tool clang-format)"
clang_tidy="$(find_tool clang-tidy)"

# No .clang-tidy config file in the repo, so nothing is enabled by default --
# spell out a sane baseline set of check categories explicitly.
CLANG_TIDY_CHECKS="-*,bugprone-*,clang-analyzer-*,performance-*,readability-*"

status=0
"${clang_format}" --dry-run --Werror "$@" || status=$?
"${clang_tidy}" --quiet "--checks=${CLANG_TIDY_CHECKS}" "$@" -- -std=c++17 || status=$?
exit "${status}"
