"""The record of each sweep: when it ran, the sites it searched, and what it posted or why it failed.

``services/sweep.py`` starts a run before each sweep and finishes it after; the
dashboard reads them back. Only the latest KEEP_RUNS are kept.
"""
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bot.helpers.post import Post
from db.session import connect
from schemas.enums import RunStatus
from services.errors import AppError

# About a month, at one sweep every 90 minutes
KEEP_RUNS = 500

INTERRUPTED = "Stopped part way: the API restarted during the sweep"


class RunNotFound(AppError):
    status = 404


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def row_to_run(row: sqlite3.Row) -> Dict[str, Any]:
    post = None
    if row["status"] == RunStatus.POSTED.value:
        post = {"site": row["site"], "title": row["title"], "article_url": row["article_url"],
                "reddit_url": row["reddit_url"]}
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "status": row["status"],
        "sites_searched": [site for site in row["sites_searched"].split(",") if site],
        "post": post,
        "error": row["error"],
        "error_details": row["error_details"],
    }


def start_run(started_at: Optional[datetime] = None) -> int:
    """Record a sweep that's beginning. Its id is what finish_run takes."""
    conn = connect()
    try:
        cursor = conn.execute("INSERT INTO runs (started_at, status) VALUES (?, ?)",
                              (timestamp(started_at or utc_now()), RunStatus.RUNNING.value))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def finish_run(run_id: int, status: RunStatus, sites_searched: List[str], post: Optional[Post] = None,
               error: Optional[str] = None, error_details: Optional[str] = None) -> None:
    """Record how a sweep ended, and let the oldest runs go."""
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE runs
            SET finished_at = ?, status = ?, sites_searched = ?, site = ?, title = ?, article_url = ?,
                reddit_url = ?, error = ?, error_details = ?
            WHERE id = ?
            """,
            (timestamp(utc_now()), status.value, ",".join(sites_searched),
             post.site if post else None, post.title if post else None,
             post.article_url if post else None, post.reddit_url if post else None,
             error, error_details, run_id),
        )
        conn.execute("DELETE FROM runs WHERE id <= (SELECT id FROM runs ORDER BY id DESC LIMIT 1 OFFSET ?)",
                     (KEEP_RUNS,))
        conn.commit()
    finally:
        conn.close()


def close_interrupted_runs() -> int:
    """Runs a stopped process left "running" end as failed, so none spins on the dashboard forever.

    Called when the schedule starts: this process hasn't begun a sweep yet, so any run
    still marked running belonged to one that's gone.
    """
    conn = connect()
    try:
        cursor = conn.execute("UPDATE runs SET status = ?, error = ? WHERE status = ?",
                              (RunStatus.FAILED.value, INTERRUPTED, RunStatus.RUNNING.value))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def get_run(run_id: int) -> Dict[str, Any]:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise RunNotFound(f"No run with id {run_id}")
    return row_to_run(row)


def list_runs(limit: int) -> List[Dict[str, Any]]:
    """The latest runs, newest first."""
    conn = connect()
    try:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [row_to_run(row) for row in rows]
    finally:
        conn.close()


def last_started_at() -> Optional[datetime]:
    """When the latest sweep began, so the schedule keeps its rhythm across a restart."""
    conn = connect()
    try:
        row = conn.execute("SELECT started_at FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    return datetime.fromisoformat(row["started_at"]) if row else None


def previous_status(run_id: int) -> Optional[RunStatus]:
    """How the sweep before this one ended, if there was one.

    A sweep a restart cut short says nothing about whether the bot works, so it's passed over.
    """
    conn = connect()
    try:
        row = conn.execute("SELECT status FROM runs WHERE id < ? AND error IS NOT ? ORDER BY id DESC LIMIT 1",
                           (run_id, INTERRUPTED)).fetchone()
    finally:
        conn.close()
    return RunStatus(row["status"]) if row else None
