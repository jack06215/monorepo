import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from common.execute_async import (
    CommandResult,
    default_redactor,
    run_command_stream_async,
    run_command_stream_gen,
)


class RedactorTest(unittest.TestCase):
    def test_redact_replaces_secret_values(self) -> None:
        redactor = default_redactor(include_env=False, extra_secret_values=["s3cr3t"])
        self.assertEqual(redactor.redact("value is s3cr3t"), "value is <REDACTED>")

    def test_redact_empty_string(self) -> None:
        redactor = default_redactor(include_env=False)
        self.assertEqual(redactor.redact(""), "")

    def test_redact_replaces_env_secrets(self) -> None:
        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghtoken123"}, clear=True):
            redactor = default_redactor()
        self.assertEqual(
            redactor.redact("using ghtoken123 now"), "using <REDACTED> now"
        )

    def test_redact_matches_authorization_pattern(self) -> None:
        redactor = default_redactor(include_env=False)
        self.assertEqual(
            redactor.redact("Authorization: abc.def-123"), "<REDACTED>"
        )

    def test_redact_matches_bearer_pattern(self) -> None:
        redactor = default_redactor(include_env=False)
        self.assertEqual(redactor.redact("Bearer abc.def-123"), "<REDACTED>")

    def test_redact_matches_extra_pattern(self) -> None:
        redactor = default_redactor(
            include_env=False, extra_patterns=[r"custom-\d+"]
        )
        self.assertEqual(redactor.redact("id=custom-42"), "id=<REDACTED>")

    def test_redact_matches_aws_access_key_pattern(self) -> None:
        redactor = default_redactor(include_env=False)
        self.assertEqual(
            redactor.redact("key=AKIAABCDEFGHIJKLMNOP"), "key=<REDACTED>"
        )

    def test_redact_matches_jwt_pattern(self) -> None:
        redactor = default_redactor(include_env=False)
        token = (
            "eyJhbGciOiJIUzI1NiJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
            "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        )
        self.assertEqual(
            redactor.redact(f"auth is {token} here"), "auth is <REDACTED> here"
        )

    def test_redact_prefers_longer_secret_match(self) -> None:
        redactor = default_redactor(
            include_env=False, extra_secret_values=["1234", "12345"]
        )
        self.assertEqual(redactor.redact("x12345y"), "x<REDACTED>y")

    def test_redact_ignores_empty_extra_secret_values(self) -> None:
        redactor = default_redactor(include_env=False, extra_secret_values=[""])
        self.assertEqual(redactor.redact("hello"), "hello")


class CommandResultTest(unittest.TestCase):
    def test_check_returncode_raises_on_nonzero(self) -> None:
        result = CommandResult(
            cmd=["x"], returncode=1, stdout="o", stderr="e", combined="o\ne"
        )
        with self.assertRaises(subprocess.CalledProcessError) as ctx:
            result.check_returncode()
        self.assertEqual(ctx.exception.returncode, 1)
        self.assertEqual(ctx.exception.output, "o")
        self.assertEqual(ctx.exception.stderr, "e")

    def test_check_returncode_noop_on_zero(self) -> None:
        result = CommandResult(
            cmd=["x"], returncode=0, stdout="", stderr="", combined=""
        )
        result.check_returncode()


class RunCommandStreamGenTest(unittest.IsolatedAsyncioTestCase):
    async def test_yields_stdout_and_stderr_lines(self) -> None:
        events = [
            event
            async for event in run_command_stream_gen(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('out1'); print('err1', file=sys.stderr)",
                ]
            )
        ]

        self.assertIn(("stdout", "out1"), events)
        self.assertIn(("stderr", "err1"), events)

    async def test_redacts_yielded_lines(self) -> None:
        redactor = default_redactor(include_env=False, extra_secret_values=["hush"])

        events = [
            event
            async for event in run_command_stream_gen(
                [sys.executable, "-c", "print('hush')"],
                redactor=redactor,
            )
        ]

        self.assertEqual(events, [("stdout", "<REDACTED>")])

    async def test_builds_default_redactor_when_logger_given(self) -> None:
        logger = Mock()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-secret123"}):
            events = [
                event
                async for event in run_command_stream_gen(
                    [sys.executable, "-c", "print('sk-secret123')"],
                    logger=logger,
                )
            ]

        self.assertEqual(events, [("stdout", "<REDACTED>")])

    async def test_uses_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            events = [
                event
                async for event in run_command_stream_gen(
                    [sys.executable, "-c", "import os; print(os.getcwd())"],
                    cwd=tmpdir,
                )
            ]
            self.assertEqual(len(events), 1)
            source, line = events[0]
            self.assertEqual(source, "stdout")
            self.assertEqual(os.path.realpath(line), os.path.realpath(tmpdir))

    async def test_uses_custom_env(self) -> None:
        events = [
            event
            async for event in run_command_stream_gen(
                [
                    sys.executable,
                    "-c",
                    "import os; print(os.environ.get('CUSTOM_VAR'))",
                ],
                env={"CUSTOM_VAR": "hello", "PATH": os.environ.get("PATH", "")},
            )
        ]
        self.assertEqual(events, [("stdout", "hello")])

    async def test_stringifies_non_string_args(self) -> None:
        events = [
            event
            async for event in run_command_stream_gen(
                [sys.executable, "-c", "import sys; print(sys.argv[1])", 42]
            )
        ]
        self.assertEqual(events, [("stdout", "42")])

    async def test_raises_timeout_error_and_kills_process(self) -> None:
        events = []
        with self.assertRaises(TimeoutError):
            async for event in run_command_stream_gen(
                [
                    sys.executable,
                    "-c",
                    "import sys, os, time; print('hi'); sys.stdout.flush(); "
                    "os.close(1); os.close(2); time.sleep(5)",
                ],
                timeout=0.3,
            ):
                events.append(event)

        self.assertEqual(events, [("stdout", "hi")])


class RunCommandStreamAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_collects_stdout_and_stderr(self) -> None:
        result = await run_command_stream_async(
            [
                sys.executable,
                "-c",
                "import sys; print('a'); print('b', file=sys.stderr)",
            ]
        )

        self.assertEqual(result.stdout, "a")
        self.assertEqual(result.stderr, "b")

    async def test_returncode_is_always_zero_regardless_of_exit_status(self) -> None:
        # Documents a real bug in run_command_stream_async: CommandResult.returncode
        # is hardcoded to 0 (see execute_async.py L200) rather than populated from
        # proc.wait(), so `check=True` can never raise CalledProcessError even when
        # the subprocess exits non-zero.
        result = await run_command_stream_async(
            [sys.executable, "-c", "import sys; sys.exit(1)"]
        )
        self.assertEqual(result.returncode, 0)

    async def test_combined_contains_both_streams(self) -> None:
        result = await run_command_stream_async(
            [
                sys.executable,
                "-c",
                "import sys; print('a'); print('b', file=sys.stderr)",
            ]
        )
        self.assertEqual(sorted(result.combined.split("\n")), ["a", "b"])

    async def test_cmd_reflects_stringified_args(self) -> None:
        result = await run_command_stream_async(
            [sys.executable, "-c", "import sys; print(sys.argv[1])", 42]
        )
        self.assertEqual(result.cmd[-1], "42")
        self.assertEqual(result.stdout, "42")

    async def test_uses_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await run_command_stream_async(
                [sys.executable, "-c", "import os; print(os.getcwd())"],
                cwd=tmpdir,
            )
        self.assertEqual(
            os.path.realpath(result.stdout), os.path.realpath(tmpdir)
        )

    async def test_builds_default_redactor_when_logger_given(self) -> None:
        logger = Mock()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-secret123"}):
            result = await run_command_stream_async(
                [sys.executable, "-c", "print('sk-secret123')"],
                logger=logger,
            )
        self.assertEqual(result.stdout, "<REDACTED>")


if __name__ == "__main__":
    unittest.main()
