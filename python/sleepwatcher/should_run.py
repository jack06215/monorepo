import sys

from sleepwatcher.functions import sleepwatcher_db_client


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: should_run.py wake|sleep", file=sys.stderr)
        return 2

    mode = sys.argv[1]

    if mode == "wake":
        key = sleepwatcher_db_client.RUN_ON_WAKE
    elif mode == "sleep":
        key = sleepwatcher_db_client.RUN_ON_SLEEP
    else:
        print("invalid mode", file=sys.stderr)
        return 2

    value = sleepwatcher_db_client.get_var(key)
    return 0 if value == "1" else 1


if __name__ == "__main__":
    raise SystemExit(main())
