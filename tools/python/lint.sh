#!/usr/bin/env bash
# Runs ruff check + mypy over a py_library/py_binary's srcs without modifying them.
# Invoked as: lint.sh <ruff> <mypy> <src>...
set -euo pipefail

ruff="$(pwd)/$1"
shift
mypy="$(pwd)/$1"
shift

status=0
"${ruff}" check "$@" || status=$?
"${mypy}" --ignore-missing-imports --explicit-package-bases "$@" || status=$?
exit "${status}"
