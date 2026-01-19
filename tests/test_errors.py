from __future__ import annotations

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.routing import Route
from starlette.testclient import TestClient

from z8ter.core import Z8ter
from z8ter.errors import register_exception_handlers


async def _trigger_http(request):
    raise HTTPException(status_code=418, detail="teapot")


async def _trigger_server(request):
    raise RuntimeError("boom")


def test_error_handlers_return_json_payloads() -> None:
    routes = [
        Route("/http", _trigger_http),
        Route("/server", _trigger_server),
    ]
    starlette_app = Starlette(routes=routes)

    register_exception_handlers(Z8ter(starlette_app=starlette_app, debug=False))
    client = TestClient(starlette_app, raise_server_exceptions=False)

    resp = client.get("/http")
    assert resp.status_code == 418
    assert resp.json() == {"ok": False, "error": {"message": "teapot"}}

    resp = client.get("/server")
    assert resp.status_code == 500
    assert resp.json() == {"ok": False, "error": {"message": "Internal server error"}}
