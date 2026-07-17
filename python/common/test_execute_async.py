import sys
import unittest

from common.execute_async import (
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


if __name__ == "__main__":
    unittest.main()
