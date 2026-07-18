import os
import sys
from collections.abc import Iterable
from pathlib import Path


def is_wsl() -> bool:
    return (
        os.uname().sysname.lower() == "linux"
        and "microsoft" in os.uname().release.lower()
    )


def is_darwin() -> bool:
    return os.uname().sysname.lower() == "darwin"


def is_termux() -> bool:
    return (
        os.uname().sysname.lower() == "linux"
        and "android" in os.uname().release.lower()
    )


def _require_env_vars(
    names: Iterable[str],
    *,
    prefix: str = "Environment variable",
) -> None:
    missing = [name for name in names if not os.getenv(name)]

    if missing:
        formatted = ", ".join(f"`{name}`" for name in missing)
        raise ValueError(f"{prefix} {formatted} is not set.")


def check_environ_openai() -> None:
    _require_env_vars(
        [
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
        ]
    )


def check_environ_ollama() -> None:
    _require_env_vars(["OLLAMA_MODEL"])


def check_environ_azure_openai() -> None:
    _require_env_vars(
        [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT_NAME",
            "AZURE_OPENAI_ENDPOINT",
            "OPENAI_API_VERSION",
        ]
    )


def detect_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "linux":
        if is_wsl():
            return "wsl"
        elif is_termux():
            return "termux"
        else:
            return "linux"
    if sys.platform == "darwin":
        return "macos"
    return "unknown"


def user_root() -> Path:
    if is_wsl():
        win_user = os.environ["WIN_USERNAME"]
        return Path("/mnt/c/Users") / win_user

    return Path.home()
