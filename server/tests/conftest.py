"""Test setup: a throwaway data folder, never ``server/data``, and no Reddit account.

Run from ``server/``:  ``pip install pytest`` then ``python -m pytest``.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="listbot-tests-"))
os.environ["LISTBOT_ENV_FILE"] = ""  # ignore a developer's server/.env, and its Reddit account
os.environ["LISTBOT_DATA_DIR"] = str(_TMP)
os.environ["LISTBOT_AUTH_DISABLED"] = "false"
os.environ["LISTBOT_SCHEDULE_ENABLED"] = "false"  # the tests start the schedule themselves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.tokens import PUBLIC_KEY_PEM, make_token  # noqa: E402

# The tools dashboard's public key, as the deployed settings hold it
os.environ["LISTBOT_AUTH_PUBLIC_KEY"] = PUBLIC_KEY_PEM

from fastapi.testclient import TestClient  # noqa: E402

from db.session import connect  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Signed in, like the app once someone has signed in on the dashboard."""
    # Entering the client runs the app's startup, which creates the tables
    with TestClient(app, headers={"Authorization": f"Bearer {make_token()}"}) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def anonymous_client() -> TestClient:
    """Nobody signed in."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def no_runs(client):
    """An empty record of sweeps: the runs are one list, so each test that reads it starts from none."""
    conn = connect()
    try:
        conn.execute("DELETE FROM runs")
        conn.commit()
    finally:
        conn.close()
