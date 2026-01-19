from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from z8ter.auth.middleware import AuthSessionMiddleware


class _SessionRepo:
    def __init__(self) -> None:
        self._sessions = {"good": "user-123"}

    def insert(self, **kwargs) -> None:  # pragma: no cover - not used in tests
        raise NotImplementedError

    def revoke(self, **kwargs) -> bool:  # pragma: no cover - not used in tests
        raise NotImplementedError

    def get_user_id(self, sid_plain: str) -> str | None:
        return self._sessions.get(sid_plain)


class _UserRepo:
    def get_user_by_id(self, user_id: str) -> dict | None:
        if user_id == "user-123":
            return {"id": user_id, "email": "user@example.com"}
        return None


async def _whoami(request):
    user = getattr(request.state, "user", None)
    return JSONResponse({"user": user})


def _make_app() -> Starlette:
    routes = [Route("/", _whoami)]
    app = Starlette(routes=routes)
    app.state.session_repo = _SessionRepo()
    app.state.user_repo = _UserRepo()
    app.add_middleware(AuthSessionMiddleware)
    return app


def test_middleware_sets_user_when_session_cookie_valid() -> None:
    client = TestClient(_make_app())
    client.cookies.set("z8_auth_sid", "good")
    resp = client.get("/")

    assert resp.status_code == 200
    assert resp.json()["user"] == {"id": "user-123", "email": "user@example.com"}


def test_middleware_leaves_user_none_when_cookie_missing() -> None:
    client = TestClient(_make_app())
    resp = client.get("/")

    assert resp.status_code == 200
    assert resp.json()["user"] is None


def test_middleware_handles_unknown_session() -> None:
    client = TestClient(_make_app())
    client.cookies.set("z8_auth_sid", "nope")
    resp = client.get("/")

    assert resp.status_code == 200
    assert resp.json()["user"] is None
