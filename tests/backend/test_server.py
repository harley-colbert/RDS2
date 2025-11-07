import pytest

from backend.server import create_app


def test_favicon_route_returns_empty_response() -> None:
    app = create_app()

    for route in app.routes:
        if getattr(route, "path", None) == "/favicon.ico":
            response = route.endpoint()
            assert response.status_code == 204
            assert response.body == b""
            break
    else:
        pytest.fail("/favicon.ico route is not registered")
