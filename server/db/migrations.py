"""Creates the tables. Runs on startup (``main.py``).

The bot itself keeps nothing: Reddit is its memory of what's been posted. This
database only records each sweep, for the dashboard.
"""
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
                -- Why it didn't finish: one line, then the traceback
                error TEXT,
                error_details TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()
