# import re
# from dataclasses import dataclass, field
# from pathlib import Path
# from subprocess import CalledProcessError

# from common.execute import (
#     CommandResult,
#     default_redactor,
#     run_command,
#     run_command_stream,
# )
# from common.logging_util import get_logger

# LOGGER = get_logger(__name__)


# @dataclass
# class Args:
#     aws_profile: str
#     bucket: str


# @dataclass
# class S3Key:
#     bucket: str
#     key_prefix: str | None = None
#     key: str = field(init=False)

#     def __post_init__(self) -> None:
#         self.key = self.key_prefix.rstrip("/") + "/" if self.key_prefix else ""


# def aws_cmd(profile: str, *args: str) -> list[str]:
#     """Build an AWS CLI command with profile."""
#     return ["aws", "--profile", profile, *args]


# class AwsSyncProgressPrinter:
#     """Print AWS S3 sync progress with throttling."""

#     _PROGRESS_RE = re.compile(r"^Completed\s+([\d.]+)\s+MiB/([\d.]+)\s+MiB")

#     def __init__(self, min_delta_mib: float = 10.0) -> None:
#         self._last_printed: float | None = None
#         self._min_delta = min_delta_mib

#     def __call__(self, line: str) -> None:
#         # Always show actual file transfers
#         if line.startswith("download:"):
#             print(line)
#             return

#         m = self._PROGRESS_RE.match(line)
#         if not m:
#             return

#         completed = float(m.group(1))
#         total = float(m.group(2))

#         if (
#             self._last_printed is None
#             or completed - self._last_printed >= self._min_delta
#             or completed >= total
#         ):
#             print(f"Progress: {completed:.1f}/{total:.1f} MiB")
#             self._last_printed = completed


# def get_caller_identity(profile: str) -> CommandResult:
#     return run_command(
#         aws_cmd(profile, "sts", "get-caller-identity"),
#         logger=LOGGER,
#         redactor=default_redactor(),
#     )


# def check_s3_list_permission(profile: str, bucket: str) -> CommandResult:
#     return run_command(
#         aws_cmd(
#             profile,
#             "s3api",
#             "head-bucket",
#             "--bucket",
#             bucket,
#         ),
#         logger=LOGGER,
#         redactor=default_redactor(),
#     )


# def list_blob_prefix(profile: str, s3_key: S3Key) -> CommandResult:
#     return run_command(
#         aws_cmd(
#             profile,
#             "s3api",
#             "list-objects-v2",
#             "--bucket",
#             s3_key.bucket,
#             "--prefix",
#             s3_key.key,
#         ),
#         logger=LOGGER,
#         redactor=default_redactor(),
#     )


# def sync_s3_prefix_to_local(
#     profile: str,
#     s3_key: S3Key,
#     local_base_dir: Path,
# ) -> CommandResult:
#     """Recursively copy all S3 objects under a prefix into a local directory."""
#     local_target = local_base_dir / s3_key.bucket / (s3_key.key_prefix or "")
#     local_target.mkdir(parents=True, exist_ok=True)

#     return run_command_stream(
#         aws_cmd(
#             profile,
#             "s3",
#             "sync",
#             f"s3://{s3_key.bucket}/{s3_key.key}",
#             local_target.as_posix(),
#         ),
#         logger=LOGGER,
#         redactor=default_redactor(),
#         line_handler=AwsSyncProgressPrinter(min_delta_mib=20.0),
#     )


# def main(args: Args) -> None:
#     try:
#         # Example: permission check
#         # check_s3_list_permission(
#         #     profile=args.aws_profile,
#         #     bucket=args.bucket,
#         # )

#         # Example: identity check
#         res = get_caller_identity(args.aws_profile)
#         print(res.stdout)

#     except CalledProcessError as e:
#         LOGGER.error(
#             "AWS command failed (exit=%s): %s",
#             e.returncode,
#             " ".join(map(str, e.cmd)),
#         )
#         raise


# if __name__ == "__main__":
#     main(
#         Args(
#             aws_profile=AWS_PROFILE,
#             bucket=BUCKET_STRADA_STG,
#         )
#     )
