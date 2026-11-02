from datetime import timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from services.auth import check_token
from services.errors import AppError
from tests.tokens import PUBLIC_KEY_PEM, make_token


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health_needs_no_sign_in(anonymous_client):
    assert anonymous_client.get("/health").status_code == 200


def test_the_root_needs_no_sign_in(anonymous_client):
    # App Service's Always On calls it to keep the API, and its schedule, running
    assert anonymous_client.get("/").status_code == 200


@pytest.mark.parametrize("path", ["/runs", "/status"])
def test_data_needs_a_sign_in(anonymous_client, path):
    response = anonymous_client.get(path)
    assert response.status_code == 401
    assert response.json() == {"detail": "Sign in to continue"}


def test_a_dashboard_token_for_this_app_opens_it(anonymous_client):
    assert anonymous_client.get("/runs", headers=bearer(make_token())).status_code == 200


@pytest.mark.parametrize("token", [
    make_token(audience=("tools-dashboard",)),  # an account without this app
    make_token(audience=("tools-dashboard", "spending-insights")),
    make_token(expires_in=timedelta(minutes=-1)),
    make_token(issuer="someone-else"),
    make_token(key=Ed25519PrivateKey.generate()),  # not signed by the dashboard
    "not-a-token",
])
def test_other_tokens_are_refused(anonymous_client, token):
    response = anonymous_client.get("/runs", headers=bearer(token))
    assert response.status_code == 401


def test_claims_say_who_it_is():
    assert check_token(make_token(), public_key=PUBLIC_KEY_PEM, disabled=False)["email"] == "person@example.com"


def test_turned_off_lets_anyone_in():
    assert check_token(None, public_key="", disabled=True) == {}


def test_without_a_key_everyone_is_refused():
    with pytest.raises(AppError) as error:
        check_token(make_token(), public_key="", disabled=False)
    assert error.value.status == 503
