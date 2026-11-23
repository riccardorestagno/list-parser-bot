"""Creates the tables, and adds the columns a database made before them lacks. Runs on startup (``main.py``).

The bot itself keeps nothing: Reddit is its memory of what's been posted. This
database only records each sweep, for the dashboard.
"""
import sqlite3

from db.session import connect


def init_db():
    conn = connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                -- UTC, ISO 8601 with the offset, so the browser shows them in its own time
                started_at TEXT NOT NULL,
                finished_at TEXT,
                -- A RunStatus value (schemas/enums.py)
                status TEXT NOT NULL,
                -- The sites searched, in the order searched, comma-separated
                sites_searched TEXT NOT NULL DEFAULT '',
                -- What was posted; NULL unless the status is posted
                site TEXT,
                title TEXT,
                article_url TEXT,
                reddit_url TEXT,
                -- Why it didn't finish: one line, then the traceback(s), a failed site's under its name
                error TEXT,
                error_details TEXT,
                -- The sites it couldn't search to the end, as JSON: [{"site", "status", "error"}]. NULL on
                -- runs from before it was kept, and until the run finishes
                site_errors TEXT
            )
        """)
        run_migrations(conn)
        conn.commit()
    finally:
        conn.close()


def run_migrations(conn: sqlite3.Connection) -> None:
    """Adds the columns a database made by an earlier release lacks. init_db commits."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
    if "site_errors" not in columns:
        # NULL on the runs already there: they didn't record how each site went
        conn.execute("ALTER TABLE runs ADD COLUMN site_errors TEXT")
