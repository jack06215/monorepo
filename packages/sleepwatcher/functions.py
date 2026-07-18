import sqlite3
from pathlib import Path

_DB_CONNECTION_STRING = Path("~/db.sqlite").expanduser()


class SleepwatchRepo:
    RUN_ON_WAKE = "SLEEPWATCHER_TEAMSPIRIT_RUN_ON_WAKE"
    RUN_ON_SLEEP = "SLEEPWATCHER_TEAMSPIRIT_RUN_ON_SLEEP"

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS shell_vars (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    updated_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    CHECK (name GLOB '[A-Z_]*')
                );
                """
            )

    def get_var(self, name: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM shell_vars WHERE name = ?",
                (name,),
            ).fetchone()
            return row[0] if row else None

    def set_run_on_wake(self, enabled: bool) -> None:
        self._set_flag(self.RUN_ON_WAKE, enabled)

    def set_run_on_sleep(self, enabled: bool) -> None:
        self._set_flag(self.RUN_ON_SLEEP, enabled)

    def _set_flag(self, name: str, enabled: bool) -> None:
        value = "1" if enabled else "0"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO shell_vars (name, value)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    value = excluded.value,
                    updated_at = unixepoch()
                """,
                (name, value),
            )


sleepwatcher_db_client = SleepwatchRepo(db_path=_DB_CONNECTION_STRING)
