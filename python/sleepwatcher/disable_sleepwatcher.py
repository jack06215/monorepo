from sleepwatcher.functions import sleepwatcher_db_client


def main() -> None:
    sleepwatcher_db_client.set_run_on_sleep(False)
    sleepwatcher_db_client.set_run_on_wake(False)


if __name__ == "__main__":
    main()
