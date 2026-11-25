"""The record of each sweep: when it ran, the sites it searched, and what it posted or why it failed.

``services/sweep.py`` starts a run before each sweep and finishes it after; the
dashboard reads them back. Only the latest KEEP_RUNS are kept.
"""
import itertools
import json
import sqlite3
from datetime import datetime, UTC
from typing import Any

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
    return datetime.now(UTC)


def timestamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def row_to_run(row: sqlite3.Row) -> dict[str, Any]:
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
        # NULL on runs from before sites were recorded one by one
        "site_errors": json.loads(row["site_errors"]) if row["site_errors"] else [],
        "post": post,
        "error": row["error"],
        "error_details": row["error_details"],
    }


def start_run(started_at: datetime | None = None) -> int:
    """Record a sweep that's beginning. Its id is what finish_run takes."""
    conn = connect()
    try:
        cursor = conn.execute("INSERT INTO runs (started_at, status) VALUES (?, ?)",
                              (timestamp(started_at or utc_now()), RunStatus.RUNNING.value))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def finish_run(run_id: int, status: RunStatus, sites_searched: list[str], post: Post | None = None,
               error: str | None = None, error_details: str | None = None,
               site_errors: list[dict[str, str]] | None = None) -> None:
    """Record how a sweep ended, and let the oldest runs go.

    ``error`` is what stopped the sweep as a whole; ``site_errors`` the sites it couldn't search to the end
    (site, status, error), each searched site without one having gone fine.
    """
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE runs
            SET finished_at = ?, status = ?, sites_searched = ?, site = ?, title = ?, article_url = ?,
                reddit_url = ?, error = ?, error_details = ?, site_errors = ?
            WHERE id = ?
            """,
            (timestamp(utc_now()), status.value, ",".join(sites_searched),
             post.site if post else None, post.title if post else None,
             post.article_url if post else None, post.reddit_url if post else None,
             error, error_details, json.dumps(site_errors or []), run_id),
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


def get_run(run_id: int) -> dict[str, Any]:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise RunNotFound(f"No run with id {run_id}")
    return row_to_run(row)


def list_runs(limit: int) -> list[dict[str, Any]]:
    """The latest runs, newest first."""
    conn = connect()
    try:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [row_to_run(row) for row in rows]
    finally:
        conn.close()


def last_started_at() -> datetime | None:
    """When the latest sweep began, so the schedule keeps its rhythm across a restart."""
    conn = connect()
    try:
        row = conn.execute("SELECT started_at FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    return datetime.fromisoformat(row["started_at"]) if row else None


def sweep_failed_before(run_id: int) -> bool:
    """Whether the sweep before this one failed as a whole (Reddit refusing the bot, or a bug), rather than a site.

    Sweeps that say nothing about it are passed over: one a restart cut short, and one Reddit was out of reach for.
    """
    conn = connect()
    try:
        row = conn.execute(
            "SELECT status, error FROM runs"
            " WHERE id < ? AND status != ? AND error IS NOT ? AND NOT (status = ? AND error IS NOT NULL)"
            " ORDER BY id DESC LIMIT 1",
            (run_id, RunStatus.RUNNING.value, INTERRUPTED, RunStatus.UNREACHABLE.value),
        ).fetchone()
    finally:
        conn.close()
    return row is not None and row["status"] == RunStatus.FAILED.value and row["error"] is not None


# A site's search, as site_history gives it: when the sweep began, and the site's error then (None when it went fine)
type SiteSearched = tuple[str, dict[str, str] | None]


def site_history(before_id: int | None = None) -> dict[str, list[SiteSearched]]:
    """Each site's searches, newest first, from the runs that recorded how each site went (not those from before)."""
    conn = connect()
    try:
        query = "SELECT started_at, sites_searched, site_errors FROM runs WHERE site_errors IS NOT NULL"
        params: tuple[Any, ...] = ()
        if before_id is not None:
            query += " AND id < ?"
            params = (before_id,)
        rows = conn.execute(query + " ORDER BY id DESC", params).fetchall()
    finally:
        conn.close()

    history: dict[str, list[SiteSearched]] = {}
    for row in rows:
        errors = {error["site"]: error for error in json.loads(row["site_errors"])}
        for site in row["sites_searched"].split(","):
            if site:
                history.setdefault(site, []).append((row["started_at"], errors.get(site)))
    return history


def sites_failing_before(run_id: int, sites: list[str]) -> set[str]:
    """Which of these sites were failing the last time a sweep before this one searched them.

    The times a site couldn't be reached are passed over: they say nothing about whether its parser works.
    """
    if not sites:
        return set()
    history = site_history(before_id=run_id)
    failing = set()
    for site in sites:
        for _, error in history.get(site, []):
            if error is not None and error["status"] == RunStatus.UNREACHABLE.value:
                continue
            if error is not None:
                failing.add(site)
            break
    return failing


def site_problems(sites: list[str]) -> list[dict[str, str]]:
    """The sites whose latest search went wrong: how (that search's error), and since when (the first of the
    searches in a row that went wrong). A site whose latest search went fine, or that no sweep recorded, has none."""
    history = site_history()
    problems = []
    for site in sites:
        streak = list(itertools.takewhile(lambda search: search[1] is not None, history.get(site, [])))
        if streak:
            problems.append({**streak[0][1], "since": streak[-1][0]})
    return problems
