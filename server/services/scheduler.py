"""Sweeps on a schedule, inside the API's process.

App Service keeps the API running (Always On), so a thread here takes the place of
the bot's old sleep loop: one sweep every SWEEP_MINUTES, timed from the start of the
last one recorded, so a restart or a deploy neither sweeps early nor skips one. A
sweep that fails is recorded and the next one runs on time.
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from services import runs
from services.sweep import run_sweep
from settings import SWEEP_MINUTES

log = logging.getLogger(__name__)


def next_sweep_at(last_started: Optional[datetime], now: datetime, interval: timedelta) -> datetime:
    """An interval after the last sweep began, or now when that has passed (or there was none)."""
    if last_started is None:
        return now
    return max(now, last_started + interval)


class Scheduler:
    def __init__(self, interval: timedelta, sweep: Callable[[], Any]):
        self.interval = interval
        self._sweep = sweep
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.next_run_at: Optional[datetime] = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running and not self._stop.is_set():
            return
        if self._thread is not None:
            self._thread.join()
        runs.close_interrupted_runs()
        self.next_run_at = next_sweep_at(runs.last_started_at(), runs.utc_now(), self.interval)
        # Each start has its own: a thread stopped mid-sweep still ends after it, whatever starts next
        self._stop = threading.Event()
        # A daemon, so a sweep under way never holds up the process stopping; the next start closes its run
        self._thread = threading.Thread(target=self._loop, args=(self._stop, self.next_run_at),
                                        name="sweep-schedule", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            # Still finishing a sweep: kept, so starting again waits for it rather than sweeping alongside it
            if not self._thread.is_alive():
                self._thread = None
        self.next_run_at = None

    def describe(self) -> Dict[str, Any]:
        next_run_at = self.next_run_at
        return {
            "enabled": self.running and not self._stop.is_set(),
            "interval_minutes": int(self.interval.total_seconds() // 60),
            "next_run_at": runs.timestamp(next_run_at) if next_run_at and self.running else None,
        }

    def _loop(self, stop: threading.Event, due: datetime) -> None:
        while not stop.wait(max(0.0, (due - runs.utc_now()).total_seconds())):
            started = runs.utc_now()
            try:
                self._sweep()
            except Exception:
                # run_sweep records its own failures: this only keeps the schedule going when recording fails too
                log.exception("A sweep failed before it could be recorded")
            due = next_sweep_at(started, runs.utc_now(), self.interval)
            if not stop.is_set():
                self.next_run_at = due


scheduler = Scheduler(timedelta(minutes=SWEEP_MINUTES), run_sweep)
