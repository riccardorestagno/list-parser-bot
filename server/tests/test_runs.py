"""Runs: the record of sweeps the dashboard lists, newest first."""
import pytest

from db.migrations import init_db
from db.session import connect
from schemas.enums import RunStatus
from services import runs


def finished_runs(count: int) -> list[int]:
    ids = [runs.start_run() for _ in range(count)]
    for run_id in ids:
        runs.finish_run(run_id, RunStatus.NOTHING_NEW, ["Cracked", "Screen Rant"])
    return ids


def test_none_yet(client, no_runs):
    assert client.get("/runs").json() == {"runs": []}


def test_newest_first_and_as_many_as_asked(client, no_runs):
    ids = finished_runs(3)
    listed = client.get("/runs", params={"limit": 2}).json()["runs"]
    assert [run["id"] for run in listed] == [ids[2], ids[1]]
    assert listed[0]["status"] == "nothing-new"
    assert listed[0]["sites_searched"] == ["Cracked", "Screen Rant"]
    assert listed[0]["post"] is None


@pytest.mark.parametrize("limit", [0, 101])
def test_the_limit_is_checked(client, limit):
    assert client.get("/runs", params={"limit": limit}).status_code == 422


def test_a_sweep_under_way_shows(client, no_runs):
    runs.start_run()
    run = client.get("/runs").json()["runs"][0]
    assert run["status"] == "running"
    assert run["finished_at"] is None
    assert run["sites_searched"] == []


def test_only_the_latest_are_kept(no_runs, monkeypatch):
    monkeypatch.setattr(runs, "KEEP_RUNS", 3)
    ids = finished_runs(5)
    assert [run["id"] for run in runs.list_runs(10)] == ids[:1:-1]


def test_runs_a_stopped_process_left_open_end_as_failed(no_runs):
    run_id = runs.start_run()
    assert runs.close_interrupted_runs() == 1
    run = runs.get_run(run_id)
    assert run["status"] == "failed"
    assert run["error"] == runs.INTERRUPTED


def test_an_unknown_run(no_runs):
    with pytest.raises(runs.RunNotFound):
        runs.get_run(123456)


def test_the_sites_a_sweep_couldnt_search_are_listed(client, no_runs):
    run_id = runs.start_run()
    runs.finish_run(run_id, RunStatus.NOTHING_NEW, ["Cracked", "Screen Rant"],
                    site_errors=[{"site": "Cracked", "status": "failed", "error": "HTTP 403 from https://www.cracked.com/"}])
    [run] = client.get("/runs").json()["runs"]
    assert run["site_errors"] == [{"site": "Cracked", "status": "failed", "error": "HTTP 403 from https://www.cracked.com/"}]


def test_a_database_from_before_gets_the_new_column_and_keeps_its_runs(no_runs):
    conn = connect()
    try:
        conn.execute("DROP TABLE runs")
        # The table as releases before site_errors made it
        conn.execute("""
            CREATE TABLE runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL, finished_at TEXT,
                status TEXT NOT NULL, sites_searched TEXT NOT NULL DEFAULT '', site TEXT, title TEXT,
                article_url TEXT, reddit_url TEXT, error TEXT, error_details TEXT
            )
        """)
        conn.execute("INSERT INTO runs (started_at, status, sites_searched, error) VALUES (?, 'failed', 'Cracked', ?)",
                     ("2026-11-01T12:00:00+00:00", "ValueError: The page changed"))
        conn.commit()
    finally:
        conn.close()

    init_db()
    init_db()  # and again, as every start does
    [run] = runs.list_runs(10)
    assert (run["status"], run["error"], run["site_errors"]) == ("failed", "ValueError: The page changed", [])
