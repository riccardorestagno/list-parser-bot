"""/health, which says the API is up and which release it runs, and stays quick while other requests wait."""
import inspect

from fastapi.routing import APIRoute

from api.routes import runs, status


def test_health_names_the_release(client):
    response = client.get("/health")
    assert response.status_code == 200
    # No version.txt in a clone: deploy.yml writes it into the package
    assert response.json() == {"status": "ok", "version": "dev"}


def test_routes_that_read_the_database_dont_hold_up_the_others():
    # An async route runs on the event loop: while it waits on a locked database (up to 30 s on Azure's
    # file share), every other request waits too, /health included. A plain def runs on a thread of its own
    routes = [route for module in (runs, status) for route in module.router.routes if isinstance(route, APIRoute)]
    assert routes
    assert [route.path for route in routes if inspect.iscoroutinefunction(route.endpoint)] == []
