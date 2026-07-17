import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from common.execute import (
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


if __name__ == "__main__":
    unittest.main()
