import asyncio
import logging
import os
import re
import subprocess
from collections.abc import AsyncIterator, Iterable, Sequence
from dataclasses import dataclass
from re import Pattern
from typing import Literal

LineEvent = tuple[Literal["stdout", "stderr"], str]


@dataclass(frozen=True, slots=True)
class Redactor:
    secret_values: tuple[str, ...] = ()
    patterns: tuple[Pattern[str], ...] = ()

    def redact(self, s: str) -> str:
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

    return Redactor(
        secret_values=tuple(sorted(set(secrets), key=len, reverse=True)),
        patterns=tuple(re.compile(p) for p in pattern_strings),
    )


@dataclass(frozen=True, slots=True)
class CommandResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str
    combined: str

    def check_returncode(self) -> None:
        if self.returncode != 0:
            raise subprocess.CalledProcessError(
                self.returncode,
                self.cmd,
                output=self.stdout,
                stderr=self.stderr,
            )


async def run_command_stream_gen(
    args: Sequence[str | int | float],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    logger: logging.Logger | None = None,
    redactor: Redactor | None = None,
) -> AsyncIterator[LineEvent]:
    """Async generator yielding (source, line) as soon as output arrives."""
    cmd = [str(a) for a in args]
    redactor = redactor or (default_redactor() if logger else None)

    if logger:
        logger.info(
            "Running command: %s",
            redactor.redact(" ".join(cmd)) if redactor else " ".join(cmd),
        )

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
    )

    assert proc.stdout and proc.stderr

    q: asyncio.Queue[LineEvent | None] = asyncio.Queue()

    async def reader(
        stream: asyncio.StreamReader,
        source: Literal["stdout", "stderr"],
    ) -> None:
        try:
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode(errors="replace").rstrip("\n")
                if redactor:
                    text = redactor.redact(text)
                await q.put((source, text))
        finally:
            await q.put(None)

    readers = [
        asyncio.create_task(reader(proc.stdout, "stdout")),
        asyncio.create_task(reader(proc.stderr, "stderr")),
    ]

    finished = 0

    try:
        while finished < 2:
            item = await q.get()
            if item is None:
                finished += 1
                continue
            yield item

        await asyncio.wait_for(proc.wait(), timeout=timeout)

    except TimeoutError:
        proc.kill()
        raise

    finally:
        for t in readers:
            t.cancel()


async def run_command_stream_async(
    args: Sequence[str | int | float],
    *,
    check: bool = True,
    timeout: float | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    logger: logging.Logger | None = None,
    redactor: Redactor | None = None,
) -> CommandResult:
    stdout: list[str] = []
    stderr: list[str] = []
    combined: list[str] = []

    async for source, line in run_command_stream_gen(
        args,
        cwd=cwd,
        env=env,
        timeout=timeout,
        logger=logger,
        redactor=redactor,
    ):
        combined.append(line)
        if source == "stdout":
            stdout.append(line)
        else:
            stderr.append(line)

    result = CommandResult(
        cmd=[str(a) for a in args],
        returncode=0,  # populated by wait()
        stdout="\n".join(stdout),
        stderr="\n".join(stderr),
        combined="\n".join(combined),
    )

    if check:
        result.check_returncode()

    return result
