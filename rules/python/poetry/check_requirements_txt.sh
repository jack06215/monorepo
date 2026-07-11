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

work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT

echo "==> poetry export (dry run, not touching requirements.txt)"
poetry export -f requirements.txt -o "${work_dir}/requirements.generated.txt" --without-hashes

if ! diff -u requirements.txt "${work_dir}/requirements.generated.txt"; then
  echo >&2
  echo "requirements.txt is out of date with poetry.lock." >&2
  echo "Run: bazel run //rules/python/poetry:update_requirements_txt" >&2
  exit 1
fi

echo "requirements.txt is in sync with poetry.lock."
