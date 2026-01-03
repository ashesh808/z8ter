from __future__ import annotations

import asyncio

from starlette.applications import Starlette
from starlette.requests import Request

from z8ter.auth.guards import login_required, skip_if_authenticated
from z8ter.responses import PlainTextResponse, RedirectResponse


def _make_request(path: str, query_string: bytes = b"") -> Request:
    app = Starlette()

    class Config:
        def __call__(self, key: str) -> str:
            mapping = {"LOGIN_PATH": "/login", "APP_PATH": "/app"}
            return mapping[key]

    app.state.services = {"config": Config()}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "root_path": "",
        "query_string": query_string,
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "app": app,
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, receive)
    return request


class _DummyEndpoint:
    @login_required
    async def protected(self, request: Request) -> PlainTextResponse:
        return PlainTextResponse("secret")


class _LoginEndpoint:
    @skip_if_authenticated
    async def login(self, request: Request) -> PlainTextResponse:
        return PlainTextResponse("login-page")


def test_login_required_redirects_when_user_missing() -> None:
    request = _make_request("/dashboard", query_string=b"tab=1")
    request.state.user = None

    result = asyncio.run(_DummyEndpoint().protected(request))

    assert isinstance(result, RedirectResponse)
    assert result.status_code == 303
    # The next parameter should be URL-encoded to prevent malformed URLs
    assert result.headers["location"] == "/login?next=%2Fdashboard%3Ftab%3D1"


def test_login_required_passes_through_when_user_present() -> None:
    request = _make_request("/dashboard")
    request.state.user = {"id": "user-1"}

    result = asyncio.run(_DummyEndpoint().protected(request))

    assert isinstance(result, PlainTextResponse)
    assert result.body == b"secret"


def test_skip_if_authenticated_redirects_logged_in_user() -> None:
    request = _make_request("/login")
    request.state.user = {"id": "user-2"}

    result = asyncio.run(_LoginEndpoint().login(request))

    assert isinstance(result, RedirectResponse)
    assert result.status_code == 303
    assert result.headers["location"] == "/app"


def test_skip_if_authenticated_allows_anonymous_user() -> None:
    request = _make_request("/login")
    request.state.user = None

    result = asyncio.run(_LoginEndpoint().login(request))

    assert isinstance(result, PlainTextResponse)
    assert result.body == b"login-page"
