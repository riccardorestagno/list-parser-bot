"""The SQLite connection every reader and writer of the database uses."""
import sqlite3

from settings import DB_PATH


def connect() -> sqlite3.Connection:
    """Open a connection with the settings every caller expects: rows read by column name."""
    # The data folder is configurable, so it may not exist yet.
    # SQLite would fail with an opaque "unable to open database file".
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # The schedule's thread writes while the API reads, on Azure's network file share: wait
    # out a lock rather than fail, which would leave a sweep's result unrecorded
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn
