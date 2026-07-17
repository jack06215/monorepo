import argparse

from sleepwatcher.functions import sleepwatcher_db_client


def parse_bool(value: str) -> bool:
    v = value.lower()
    if v in {"1", "true", "yes", "on", "enable", "enabled"}:
        return True
    if v in {"0", "false", "no", "off", "disable", "disabled"}:
        return False
    raise argparse.ArgumentTypeError(
        f"Invalid boolean value: {value!r} (expected true/false)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m sleepwatcher.set_run_on_sleep",
        description="Enable or disable running tasks on sleep event.",
    )
    parser.add_argument(
        "enabled",
        type=parse_bool,
        help="true|false",
    )

    args = parser.parse_args()

    sleepwatcher_db_client.set_run_on_sleep(args.enabled)


if __name__ == "__main__":
    main()
