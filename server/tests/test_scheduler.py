import threading
from datetime import datetime, timedelta, timezone

from schemas.enums import RunStatus
from services import runs
from services.scheduler import Scheduler, next_sweep_at

INTERVAL = timedelta(minutes=90)
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def test_the_first_sweep_is_right_away():
    assert next_sweep_at(None, NOW, INTERVAL) == NOW


def test_a_restart_keeps_the_rhythm():
    assert next_sweep_at(NOW - timedelta(minutes=30), NOW, INTERVAL) == NOW + timedelta(minutes=60)


def test_a_sweep_that_is_overdue_runs_now():
    assert next_sweep_at(NOW - timedelta(hours=3), NOW, INTERVAL) == NOW


def test_starting_sweeps_and_stopping_ends_it(no_runs):
    swept = threading.Event()
    scheduler = Scheduler(INTERVAL, swept.set)
    scheduler.start()
    try:
        assert swept.wait(5)
        assert scheduler.describe()["enabled"] is True
    finally:
        scheduler.stop()
    assert scheduler.describe() == {"enabled": False, "interval_minutes": 90, "next_run_at": None}


def test_after_a_recent_sweep_it_waits_its_turn(no_runs):
    run_id = runs.start_run(runs.utc_now() - timedelta(minutes=30))
    runs.finish_run(run_id, RunStatus.NOTHING_NEW, [])
    swept = threading.Event()
    scheduler = Scheduler(INTERVAL, swept.set)
    scheduler.start()
    try:
        assert not swept.wait(0.2)
        wait = datetime.fromisoformat(scheduler.describe()["next_run_at"]) - runs.utc_now()
        assert timedelta(minutes=59) < wait <= timedelta(minutes=60)
    finally:
        scheduler.stop()


def test_a_sweep_that_raises_doesnt_stop_the_schedule(no_runs):
    calls = []
    twice = threading.Event()

    def failing_sweep():
        calls.append(1)
        if len(calls) == 2:
            twice.set()
        raise RuntimeError("The database is locked")

    scheduler = Scheduler(timedelta(milliseconds=50), failing_sweep)
    scheduler.start()
    try:
        assert twice.wait(5)
    finally:
        scheduler.stop()


def test_starting_again_waits_for_a_sweep_still_finishing(no_runs):
    sweeping, release = threading.Event(), threading.Event()
    concurrent = []

    def slow_sweep():
        concurrent.append(sweeping.is_set())
        sweeping.set()
        release.wait(5)
        sweeping.clear()

    scheduler = Scheduler(INTERVAL, slow_sweep)
    scheduler.start()
    assert sweeping.wait(5)
    scheduler.stop(timeout=0.1)  # the sweep is still going
    assert scheduler.describe()["enabled"] is False
    threading.Timer(0.2, release.set).start()
    scheduler.start()  # waits for it, then sweeps again
    scheduler.stop()
    assert True not in concurrent


def test_starting_closes_the_runs_a_stopped_process_left_open(no_runs):
    run_id = runs.start_run()
    scheduler = Scheduler(INTERVAL, lambda: None)
    scheduler.start()
    scheduler.stop()
    assert runs.get_run(run_id)["status"] == "failed"
