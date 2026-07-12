#!/usr/bin/env bash
# Runs `clang-format -i` over a cc_test's srcs, editing the files in the
# actual workspace (not the sandboxed runfiles copies). Must be invoked via
# `bazel run`, which sets BUILD_WORKSPACE_DIRECTORY.
# Invoked as: fix.sh <package> <src>...
set -euo pipefail

if [[ -z "${BUILD_WORKSPACE_DIRECTORY:-}" ]]; then
  echo "error: run this target with 'bazel run', not 'bazel build/test'" >&2
  exit 1
fi

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
package="$1"
shift

files=()
for src in "$@"; do
  if [[ -z "${package}" ]]; then
    files+=("${src}")
  else
    files+=("${package}/${src}")
  fi
done

cd "${BUILD_WORKSPACE_DIRECTORY}"
"${clang_format}" -i "${files[@]}"
