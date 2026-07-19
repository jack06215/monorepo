import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from common.execute import (
    CommandResult,
    aws_cli,
    default_redactor,
    kubectl_cli,
    run_command,
    run_command_stream,
)


class RedactorTest(unittest.TestCase):
    def test_redact_empty_string_returns_as_is(self) -> None:
        redactor = default_redactor(include_env=False)
        self.assertEqual(redactor.redact(""), "")

    def test_redact_replaces_secret_values(self) -> None:
        redactor = default_redactor(
            include_env=False, extra_secret_values=["s3cr3t"]
        )
        self.assertEqual(
            redactor.redact("password is s3cr3t"), "password is <REDACTED>"
        )

    def test_redact_replaces_env_secrets(self) -> None:
        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghtoken123"}, clear=True):
            redactor = default_redactor()
        self.assertEqual(
            redactor.redact("using ghtoken123 now"), "using <REDACTED> now"
        )

    def test_redact_matches_authorization_pattern(self) -> None:
        redactor = default_redactor(include_env=False)
        self.assertEqual(
            redactor.redact("Authorization: abc.def-123"),
            "<REDACTED>",
        )

    def test_redact_matches_bearer_pattern(self) -> None:
        redactor = default_redactor(include_env=False)
        self.assertEqual(
            redactor.redact("Bearer abc.def-123"),
            "<REDACTED>",
        )

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


class RunCommandTest(unittest.TestCase):
    def test_captures_stdout_and_stderr(self) -> None:
        result = run_command(
            [
                sys.executable,
                "-c",
                "import sys; print('out-line'); print('err-line', file=sys.stderr)",
            ]
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "out-line")
        self.assertEqual(result.stderr.strip(), "err-line")

    def test_check_true_raises_on_nonzero_exit(self) -> None:
        with self.assertRaises(subprocess.CalledProcessError):
            run_command([sys.executable, "-c", "import sys; sys.exit(3)"])

    def test_check_false_returns_result_on_nonzero_exit(self) -> None:
        result = run_command(
            [sys.executable, "-c", "import sys; sys.exit(3)"], check=False
        )
        self.assertEqual(result.returncode, 3)

    def test_rejects_shell_true(self) -> None:
        with self.assertRaises(ValueError):
            run_command(["echo", "hi"], shell=True)

    def test_redacts_output_when_redactor_given(self) -> None:
        redactor = default_redactor(include_env=False, extra_secret_values=["hush"])
        result = run_command(
            [sys.executable, "-c", "print('hush')"],
            redactor=redactor,
        )
        self.assertEqual(result.stdout.strip(), "<REDACTED>")

    def test_builds_default_redactor_when_logger_given(self) -> None:
        logger = Mock()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-secret123"}):
            result = run_command(
                [sys.executable, "-c", "print('sk-secret123')"],
                logger=logger,
            )
        self.assertEqual(result.stdout.strip(), "<REDACTED>")

    def test_no_redaction_without_logger_or_redactor(self) -> None:
        result = run_command([sys.executable, "-c", "print('plain-secret')"])
        self.assertEqual(result.stdout.strip(), "plain-secret")

    def test_combined_joins_stdout_then_stderr(self) -> None:
        result = run_command(
            [
                sys.executable,
                "-c",
                "import sys; print('out'); print('err', file=sys.stderr)",
            ]
        )
        self.assertEqual(result.combined, "out\nerr")

    def test_uses_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_command(
                [sys.executable, "-c", "import os; print(os.getcwd())"],
                cwd=tmpdir,
            )
        self.assertEqual(
            os.path.realpath(result.stdout.strip()), os.path.realpath(tmpdir)
        )

    def test_uses_custom_env(self) -> None:
        result = run_command(
            [sys.executable, "-c", "import os; print(os.environ.get('CUSTOM_VAR'))"],
            env={"CUSTOM_VAR": "hello", "PATH": os.environ.get("PATH", "")},
        )
        self.assertEqual(result.stdout.strip(), "hello")

    def test_stringifies_non_string_args(self) -> None:
        result = run_command(
            [sys.executable, "-c", "import sys; print(sys.argv[1])", 42]
        )
        self.assertEqual(result.stdout.strip(), "42")


class RunCommandStreamTest(unittest.TestCase):
    def test_streams_lines_to_handlers(self) -> None:
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        result = run_command_stream(
            [
                sys.executable,
                "-c",
                "import sys; print('a'); print('b', file=sys.stderr)",
            ],
            stdout_handler=stdout_lines.append,
            stderr_handler=stderr_lines.append,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(stdout_lines, ["a"])
        self.assertEqual(stderr_lines, ["b"])

    def test_line_handler_receives_both_streams(self) -> None:
        all_lines: list[str] = []

        run_command_stream(
            [
                sys.executable,
                "-c",
                "import sys; print('a'); print('b', file=sys.stderr)",
            ],
            line_handler=all_lines.append,
        )

        self.assertEqual(sorted(all_lines), ["a", "b"])

    def test_rejects_shell_true(self) -> None:
        with self.assertRaises(ValueError):
            run_command_stream(["echo", "hi"], shell=True)

    def test_check_true_raises_on_nonzero_exit(self) -> None:
        with self.assertRaises(subprocess.CalledProcessError):
            run_command_stream([sys.executable, "-c", "import sys; sys.exit(2)"])

    def test_check_false_returns_result_on_nonzero_exit(self) -> None:
        result = run_command_stream(
            [sys.executable, "-c", "import sys; sys.exit(4)"], check=False
        )
        self.assertEqual(result.returncode, 4)

    def test_combined_contains_both_streams(self) -> None:
        result = run_command_stream(
            [
                sys.executable,
                "-c",
                "import sys; print('a'); print('b', file=sys.stderr)",
            ]
        )
        self.assertEqual(sorted(result.combined.split("\n")), ["a", "b"])

    def test_terminates_process_on_keyboard_interrupt(self) -> None:
        fake_proc = Mock()
        fake_proc.stdout = io.StringIO("")
        fake_proc.stderr = io.StringIO("")
        fake_proc.wait.side_effect = [KeyboardInterrupt(), 0]

        with patch("common.execute.subprocess.Popen", return_value=fake_proc):
            with self.assertRaises(KeyboardInterrupt):
                run_command_stream([sys.executable, "-c", "pass"])

        fake_proc.terminate.assert_called_once()

    def test_kills_process_when_terminate_times_out(self) -> None:
        fake_proc = Mock()
        fake_proc.stdout = io.StringIO("")
        fake_proc.stderr = io.StringIO("")
        fake_proc.wait.side_effect = [
            KeyboardInterrupt(),
            subprocess.TimeoutExpired(cmd="x", timeout=2),
        ]

        with patch("common.execute.subprocess.Popen", return_value=fake_proc):
            with self.assertRaises(KeyboardInterrupt):
                run_command_stream([sys.executable, "-c", "pass"])

        fake_proc.kill.assert_called_once()


class AwsCliTest(unittest.TestCase):
    def test_parses_json_output(self) -> None:
        fake_result = Mock(stdout='{"ok": true}', cmd=["aws"])
        with patch("common.execute.run_command", return_value=fake_result) as mocked:
            output = aws_cli(["s3", "ls"], profile="dev", region="us-east-1")

        self.assertEqual(output, {"ok": True})
        called_args = mocked.call_args.args[0]
        self.assertIn("--profile", called_args)
        self.assertIn("dev", called_args)
        self.assertIn("--output", called_args)
        self.assertIn("json", called_args)

    def test_raises_runtime_error_on_invalid_json(self) -> None:
        fake_result = Mock(stdout="not json", cmd=["aws"])
        with patch("common.execute.run_command", return_value=fake_result):
            with self.assertRaises(RuntimeError):
                aws_cli(["s3", "ls"])

    def test_stream_true_uses_run_command_stream(self) -> None:
        fake_result = Mock(stdout="{}", cmd=["aws"])
        with (
            patch("common.execute.run_command") as run_mock,
            patch(
                "common.execute.run_command_stream", return_value=fake_result
            ) as stream_mock,
        ):
            aws_cli(["s3", "ls"], stream=True)

        stream_mock.assert_called_once()
        run_mock.assert_not_called()

    def test_passes_timeout_through(self) -> None:
        fake_result = Mock(stdout="{}", cmd=["aws"])
        with patch("common.execute.run_command", return_value=fake_result) as mocked:
            aws_cli(["s3", "ls"], timeout=30)

        self.assertEqual(mocked.call_args.kwargs["timeout"], 30)


class KubectlCliTest(unittest.TestCase):
    def test_returns_text_output_by_default(self) -> None:
        fake_result = Mock(stdout="pod/foo   Running")
        with patch("common.execute.run_command", return_value=fake_result):
            output = kubectl_cli(["get", "pods"])

        self.assertEqual(output, "pod/foo   Running")

    def test_parses_json_output_and_adds_output_flag(self) -> None:
        fake_result = Mock(stdout='{"items": []}')
        with patch("common.execute.run_command", return_value=fake_result) as mocked:
            output = kubectl_cli(["get", "pods"], output="json")

        self.assertEqual(output, {"items": []})
        called_args = mocked.call_args.args[0]
        self.assertEqual(called_args[-2:], ["-o", "json"])

    def test_raises_runtime_error_on_invalid_json(self) -> None:
        fake_result = Mock(stdout="not json", cmd=["kubectl", "get", "pods", "-o", "json"])
        with patch("common.execute.run_command", return_value=fake_result):
            with self.assertRaises(RuntimeError):
                kubectl_cli(["get", "pods"], output="json")

    def test_does_not_duplicate_output_flag_when_already_specified(self) -> None:
        fake_result = Mock(stdout='{"items": []}')
        with patch("common.execute.run_command", return_value=fake_result) as mocked:
            kubectl_cli(["get", "pods", "-o", "wide"], output="json")

        called_args = mocked.call_args.args[0]
        self.assertEqual(called_args, ["kubectl", "get", "pods", "-o", "wide"])

    def test_stream_true_uses_run_command_stream(self) -> None:
        fake_result = Mock(stdout="pod/foo   Running")
        with (
            patch("common.execute.run_command") as run_mock,
            patch(
                "common.execute.run_command_stream", return_value=fake_result
            ) as stream_mock,
        ):
            kubectl_cli(["get", "pods"], stream=True)

        stream_mock.assert_called_once()
        run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
