#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BUILD_WORKSPACE_DIRECTORY:-}" ]]; then
  echo "error: run this via 'bazel run', not 'bazel build'." >&2
  exit 1
fi
if ! command -v poetry &>/dev/null; then
  echo "error: poetry not found on PATH." >&2
  exit 1
fi

cd "${BUILD_WORKSPACE_DIRECTORY}"

echo "==> poetry lock"
poetry lock

echo "==> poetry export -> requirements.txt"
poetry export -f requirements.txt -o requirements.txt

echo "==> done. review with 'git diff requirements.txt'"
