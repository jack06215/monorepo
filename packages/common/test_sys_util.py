import os
import unittest
from pathlib import Path
from unittest.mock import patch

from common import sys_util


def _fake_uname(sysname: str, release: str) -> os.uname_result:
    return os.uname_result(
        (sysname, "test-node", release, "#1 test version", "x86_64")
    )


class PlatformDetectionTest(unittest.TestCase):
    def test_is_wsl_true_for_linux_with_microsoft_release(self) -> None:
        with patch("os.uname", return_value=_fake_uname("Linux", "5.10.0-microsoft")):
            self.assertTrue(sys_util.is_wsl())

    def test_is_wsl_false_for_plain_linux(self) -> None:
        with patch("os.uname", return_value=_fake_uname("Linux", "5.10.0-generic")):
            self.assertFalse(sys_util.is_wsl())

    def test_is_darwin_true_on_darwin(self) -> None:
        with patch("os.uname", return_value=_fake_uname("Darwin", "23.0.0")):
            self.assertTrue(sys_util.is_darwin())

    def test_is_darwin_false_on_linux(self) -> None:
        with patch("os.uname", return_value=_fake_uname("Linux", "5.10.0")):
            self.assertFalse(sys_util.is_darwin())

    def test_is_termux_true_for_linux_with_android_release(self) -> None:
        with patch("os.uname", return_value=_fake_uname("Linux", "4.14.0-android")):
            self.assertTrue(sys_util.is_termux())

    def test_is_termux_false_for_plain_linux(self) -> None:
        with patch("os.uname", return_value=_fake_uname("Linux", "4.14.0-generic")):
            self.assertFalse(sys_util.is_termux())

    def test_detect_platform_windows(self) -> None:
        with patch("sys.platform", "win32"):
            self.assertEqual(sys_util.detect_platform(), "windows")

    def test_detect_platform_macos(self) -> None:
        with patch("sys.platform", "darwin"):
            self.assertEqual(sys_util.detect_platform(), "macos")

    def test_detect_platform_wsl(self) -> None:
        with (
            patch("sys.platform", "linux"),
            patch("os.uname", return_value=_fake_uname("Linux", "5.10.0-microsoft")),
        ):
            self.assertEqual(sys_util.detect_platform(), "wsl")

    def test_detect_platform_termux(self) -> None:
        with (
            patch("sys.platform", "linux"),
            patch("os.uname", return_value=_fake_uname("Linux", "4.14.0-android")),
        ):
            self.assertEqual(sys_util.detect_platform(), "termux")

    def test_detect_platform_plain_linux(self) -> None:
        with (
            patch("sys.platform", "linux"),
            patch("os.uname", return_value=_fake_uname("Linux", "5.10.0-generic")),
        ):
            self.assertEqual(sys_util.detect_platform(), "linux")

    def test_detect_platform_unknown(self) -> None:
        with patch("sys.platform", "freebsd"):
            self.assertEqual(sys_util.detect_platform(), "unknown")


class RequireEnvVarsTest(unittest.TestCase):
    def test_check_environ_openai_raises_when_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                sys_util.check_environ_openai()
            self.assertIn("OPENAI_API_KEY", str(ctx.exception))
            self.assertIn("OPENAI_MODEL", str(ctx.exception))

    def test_check_environ_openai_passes_when_set(self) -> None:
        env = {"OPENAI_API_KEY": "key", "OPENAI_MODEL": "gpt-test"}
        with patch.dict(os.environ, env, clear=True):
            sys_util.check_environ_openai()

    def test_check_environ_ollama_raises_when_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                sys_util.check_environ_ollama()

    def test_check_environ_azure_openai_raises_when_partially_set(self) -> None:
        env = {"AZURE_OPENAI_API_KEY": "key"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError) as ctx:
                sys_util.check_environ_azure_openai()
            self.assertIn("AZURE_OPENAI_DEPLOYMENT_NAME", str(ctx.exception))
            self.assertIn("AZURE_OPENAI_ENDPOINT", str(ctx.exception))
            self.assertIn("OPENAI_API_VERSION", str(ctx.exception))
            self.assertNotIn("`AZURE_OPENAI_API_KEY`", str(ctx.exception))

    def test_check_environ_azure_openai_passes_when_all_set(self) -> None:
        env = {
            "AZURE_OPENAI_API_KEY": "key",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "deployment",
            "AZURE_OPENAI_ENDPOINT": "https://example.com",
            "OPENAI_API_VERSION": "2024-01-01",
        }
        with patch.dict(os.environ, env, clear=True):
            sys_util.check_environ_azure_openai()


class UserRootTest(unittest.TestCase):
    def test_returns_home_when_not_wsl(self) -> None:
        with patch("common.sys_util.is_wsl", return_value=False):
            self.assertEqual(sys_util.user_root(), Path.home())

    def test_returns_windows_mount_when_wsl(self) -> None:
        with (
            patch("common.sys_util.is_wsl", return_value=True),
            patch.dict(os.environ, {"WIN_USERNAME": "jack"}, clear=True),
        ):
            self.assertEqual(sys_util.user_root(), Path("/mnt/c/Users/jack"))

    def test_raises_when_wsl_without_win_username(self) -> None:
        with (
            patch("common.sys_util.is_wsl", return_value=True),
            patch.dict(os.environ, {}, clear=True),
        ):
            with self.assertRaises(KeyError):
                sys_util.user_root()


if __name__ == "__main__":
    unittest.main()
