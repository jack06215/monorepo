from sleepwatcher.functions import sleepwatcher_db_client


def main() -> None:
    sleepwatcher_db_client.set_run_on_sleep(True)
    sleepwatcher_db_client.set_run_on_wake(True)


if __name__ == "__main__":
    main()
