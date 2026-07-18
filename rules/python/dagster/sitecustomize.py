"""Workaround for dagster-io/dagster#33851 (fix pending, unmerged: PR #33853).

Starlette's StaticFiles rejects symlinked files by default (follow_symlink=False),
and Bazel's runfiles tree serves every third-party wheel file as a symlink into
its content-addressable cache. That makes dagster-webserver 404 on every static
asset under `bazel run`, so the UI loads as a blank page.

Patch StaticFiles to default follow_symlink=True until the upstream fix ships.
Shared across every `dagster dev` py_binary under //packages via
//rules/python/dagster:sitecustomize.py -- add it to a target's `data` and
put its containing dir on PYTHONPATH for the `dagster dev` subprocess (see
packages/dagster_hello_world/main.py for the pattern). Delete this file (and
its wiring) once dagster-webserver is bumped past the release containing
that fix.
"""

import starlette.staticfiles

_original_init = starlette.staticfiles.StaticFiles.__init__


def _patched_init(self, *args, **kwargs):
    kwargs.setdefault("follow_symlink", True)
    _original_init(self, *args, **kwargs)


starlette.staticfiles.StaticFiles.__init__ = _patched_init
