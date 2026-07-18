import json
import logging
import os
import re
import subprocess
import threading
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from queue import Queue
from re import Pattern
from typing import Any, Literal, overload

LineHandler = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class Redactor:
    """Redact secrets from strings."""

    secret_values: tuple[str, ...] = ()
    patterns: tuple[Pattern[str], ...] = ()

    def redact(self, s: str) -> str:
        """Return string with secrets replaced by '<REDACTED>'."""
        if not s:
            return s

        for val in self.secret_values:
            if val and val in s:
                s = s.replace(val, "<REDACTED>")

        for pat in self.patterns:
            s = pat.sub("<REDACTED>", s)

        return s


def default_redactor(
    *,
    extra_secret_values: Iterable[str] = (),
    extra_patterns: Iterable[str] = (),
    include_env: bool = True,
) -> Redactor:
    """Build a default redactor suitable for infra / data tooling."""
    env_keys = (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AZURE_CLIENT_SECRET",
        "GITHUB_TOKEN",
        "GITLAB_TOKEN",
        "SLACK_BOT_TOKEN",
        "SLACK_TOKEN",
        "OPENAI_API_KEY",
    )

    secrets: list[str] = []

    if include_env:
        for k in env_keys:
            v = os.getenv(k)
            if v:
                secrets.append(v)

    for v in extra_secret_values:
        if v:
            secrets.append(v)

    pattern_strings = [
        r"(?i)\bauthorization\b\s*[:=]\s*\S+",
        r"(?i)\bbearer\b\s+[A-Za-z0-9\-\._=]+",
        r"(?i)\b(token|api[_-]?key|secret|password|passwd)\b\s*[:=]\s*[^ \t\r\n]+",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"\bASIA[0-9A-Z]{16}\b",
        r"\beyJ[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+?\b",
    ]
    pattern_strings.extend(extra_patterns)

    patterns = tuple(re.compile(p) for p in pattern_strings)

    secrets_sorted = tuple(sorted(set(secrets), key=len, reverse=True))

    return Redactor(secret_values=secrets_sorted, patterns=patterns)


def _stringify_args(args: Sequence[str | int | float]) -> list[str]:
    """Convert command arguments to strings."""
    return [str(a) for a in args]


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result of a subprocess execution."""

    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str
    combined: str

    def check_returncode(self) -> None:
        """Raise CalledProcessError if returncode is non-zero."""
        if self.returncode != 0:
            raise subprocess.CalledProcessError(
                self.returncode,
                self.cmd,
                output=self.stdout,
                stderr=self.stderr,
            )


def _reader_thread(
    stream: Any,
    *,
    source: Literal["stdout", "stderr"],
    q: Queue[tuple[Literal["stdout", "stderr"], str] | None],
) -> None:
    """Read lines from a stream and push them to the queue."""
    try:
        for line in iter(stream.readline, ""):
            q.put((source, line.rstrip("\n")))
    finally:
        q.put(None)


def _drain_queue(
    *,
    q: Queue[tuple[Literal["stdout", "stderr"], str] | None],
    stdout_lines: list[str],
    stderr_lines: list[str],
    combined_lines: list[str],
    stdout_handler: LineHandler | None,
    stderr_handler: LineHandler | None,
    line_handler: LineHandler | None,
    timeout: float | None,
    redactor: Redactor | None,
) -> None:
    """Drain stdout/stderr queue until both streams complete."""
    done = 0
    while done < 2:
        item = q.get(timeout=timeout) if timeout is not None else q.get()
        if item is None:
            done += 1
            continue

        source, line = item
        safe_line = redactor.redact(line) if redactor else line

        combined_lines.append(safe_line)

        if source == "stdout":
            stdout_lines.append(safe_line)
            if line_handler:
                line_handler(safe_line)
            elif stdout_handler:
                stdout_handler(safe_line)
        else:
            stderr_lines.append(safe_line)
            if line_handler:
                line_handler(safe_line)
            elif stderr_handler:
                stderr_handler(safe_line)


def run_command(
    args: Sequence[str | int | float],
    *,
    check: bool = True,
    timeout: float | None = None,
    text: bool = True,
    encoding: str = "utf-8",
    errors: str = "replace",
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    logger: logging.Logger | None = None,
    redactor: Redactor | None = None,
    **kwargs: Any,
) -> CommandResult:
    """Run a command and capture stdout/stderr safely."""
    cmd = _stringify_args(args)
    redactor = redactor or (default_redactor() if logger else None)

    if logger:
        logger.info(
            "Running command: %s",
            redactor.redact(" ".join(cmd)) if redactor else " ".join(cmd),
        )

    if kwargs.get("shell"):
        raise ValueError("shell=True is not allowed in run_command()")

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        encoding=encoding if text else None,
        errors=errors if text else None,
        timeout=timeout,
        cwd=cwd,
        env=env,
        check=False,
        **kwargs,
    )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    if redactor:
        stdout = redactor.redact(stdout)
        stderr = redactor.redact(stderr)

    combined = "\n".join(s for s in (stdout.strip("\n"), stderr.strip("\n")) if s)

    result = CommandResult(
        cmd=cmd,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
        combined=combined,
    )

    if check:
        result.check_returncode()

    return result


def run_command_stream(
    args: Sequence[str | int | float],
    *,
    check: bool = True,
    timeout: float | None = None,
    text: bool = True,
    encoding: str = "utf-8",
    errors: str = "replace",
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    stdout_handler: LineHandler | None = None,
    stderr_handler: LineHandler | None = None,
    line_handler: LineHandler | None = None,
    logger: logging.Logger | None = None,
    redactor: Redactor | None = None,
    **kwargs: Any,
) -> CommandResult:
    """Run a command and stream stdout/stderr concurrently."""
    cmd = _stringify_args(args)
    redactor = redactor or (default_redactor() if logger else None)

    if logger:
        logger.info(
            "Running command: %s",
            redactor.redact(" ".join(cmd)) if redactor else " ".join(cmd),
        )

    if kwargs.get("shell"):
        raise ValueError("shell=True is not allowed in run_command_stream()")

    q: Queue[tuple[Literal["stdout", "stderr"], str] | None] = Queue()
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    combined_lines: list[str] = []

    proc: subprocess.Popen[str] | None = None

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=text,
            encoding=encoding if text else None,
            errors=errors if text else None,
            cwd=cwd,
            env=env,
            **kwargs,
        )

        if proc.stdout is None or proc.stderr is None:
            raise RuntimeError("Failed to open subprocess pipes")

        threading.Thread(
            target=_reader_thread,
            args=(proc.stdout,),
            kwargs={"source": "stdout", "q": q},
            daemon=True,
        ).start()

        threading.Thread(
            target=_reader_thread,
            args=(proc.stderr,),
            kwargs={"source": "stderr", "q": q},
            daemon=True,
        ).start()

        _drain_queue(
            q=q,
            stdout_lines=stdout_lines,
            stderr_lines=stderr_lines,
            combined_lines=combined_lines,
            stdout_handler=stdout_handler,
            stderr_handler=stderr_handler,
            line_handler=line_handler,
            timeout=timeout,
            redactor=redactor,
        )

        returncode = proc.wait(timeout=timeout)

    except KeyboardInterrupt:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        raise

    finally:
        if proc is not None:
            if proc.stdout is not None:
                proc.stdout.close()
            if proc.stderr is not None:
                proc.stderr.close()

    result = CommandResult(
        cmd=cmd,
        returncode=returncode,
        stdout="\n".join(stdout_lines),
        stderr="\n".join(stderr_lines),
        combined="\n".join(combined_lines),
    )

    if check:
        result.check_returncode()

    return result


def aws_cli(
    args: Sequence[str | int | float],
    *,
    logger: logging.Logger | None = None,
    profile: str | None = None,
    region: str | None = None,
    timeout: float | None = None,
    stream: bool = False,
    redactor: Redactor | None = None,
) -> dict[str, Any]:
    """Run AWS CLI and parse JSON output (forces --output json)."""
    cmd: list[str | int | float] = ["aws"]

    if profile:
        cmd += ["--profile", profile]
    if region:
        cmd += ["--region", region]

    cmd += list(args)
    cmd += ["--output", "json"]

    result = (
        run_command_stream(
            cmd,
            logger=logger,
            timeout=timeout,
            redactor=redactor,
            line_handler=(logger.info if logger else None),
            stderr_handler=(logger.warning if logger else None),
        )
        if stream
        else run_command(
            cmd,
            logger=logger,
            timeout=timeout,
            redactor=redactor,
        )
    )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            "Failed to parse AWS CLI JSON output.\n"
            f"CMD: {' '.join(result.cmd)}\n"
            f"STDOUT:\n{result.stdout}"
        ) from e


@overload
def kubectl_cli(
    args: list[str],
    *,
    output: Literal["json"],
    logger: logging.Logger | None = None,
) -> dict[str, Any]: ...
@overload
def kubectl_cli(
    args: list[str],
    *,
    output: Literal["text"] = "text",
    logger: logging.Logger | None = None,
) -> str: ...


def kubectl_cli(
    args: list[str],
    *,
    output: Literal["json", "text"] = "text",
    logger: logging.Logger | None = None,
    timeout: float | None = None,
    stream: bool = False,
    redactor: Redactor | None = None,
) -> dict[str, Any] | str:
    """Run kubectl and return text or parsed JSON."""
    cmd: list[str | int | float] = ["kubectl", *args]

    if output == "json" and "-o" not in args and "--output" not in args:
        cmd += ["-o", "json"]

    result = (
        run_command_stream(
            cmd,
            logger=logger,
            timeout=timeout,
            redactor=redactor,
            line_handler=(logger.info if logger else None),
            stderr_handler=(logger.warning if logger else None),
        )
        if stream
        else run_command(
            cmd,
            logger=logger,
            timeout=timeout,
            redactor=redactor,
        )
    )

    if output == "json":
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                "Failed to parse kubectl JSON output.\n"
                f"CMD: {' '.join(result.cmd)}\n"
                f"STDOUT:\n{result.stdout}"
            ) from e

    return result.stdout
