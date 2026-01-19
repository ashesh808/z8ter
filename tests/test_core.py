from __future__ import annotations

import asyncio

import pytest
from starlette.applications import Starlette
from starlette.routing import Route

from z8ter.core import Z8ter
from z8ter.responses import JSONResponse


def test_z8ter_debug_defaults_to_dev_mode() -> None:
    starlette_app = Starlette()
    app = Z8ter(mode="dev", starlette_app=starlette_app)

    assert app.debug is True
    assert app.mode == "dev"
    assert app.state is starlette_app.state


def test_z8ter_invalid_mode_raises() -> None:
    starlette_app = Starlette()
    with pytest.raises(ValueError):
        Z8ter(mode="invalid", starlette_app=starlette_app)


async def _ping(request):
    return JSONResponse({"ok": True})


def test_z8ter_forwards_asgi_calls() -> None:
    routes = [Route("/ping", _ping)]
    starlette_app = Starlette(routes=routes)
    app = Z8ter(starlette_app=starlette_app, debug=False)

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/ping",
        "raw_path": b"/ping",
        "scheme": "http",
        "headers": [],
        "root_path": "",
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "app": starlette_app,
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    sent = {}

    async def send(message):
        sent.setdefault("messages", []).append(message)

    asyncio.run(app(scope, receive, send))

    assert any(m["type"] == "http.response.start" for m in sent["messages"])
