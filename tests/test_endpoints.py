from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

import z8ter
from z8ter.builders import builder_functions as bf
from z8ter.core import Z8ter
from z8ter.endpoints.helpers import load_props, render


def _prime_templates() -> Z8ter:
    starlette_app = Starlette()
    starlette_app.mount(
        "/static", StaticFiles(directory=str(z8ter.STATIC_PATH)), name="static"
    )
    app = Z8ter(starlette_app=starlette_app, debug=False)
    ctx = {"app": app, "services": {}}
    bf.use_templating_builder(ctx)
    bf.use_vite_builder(ctx)
    return app


def _make_request(app: Z8ter) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "scheme": "http",
        "headers": [],
        "root_path": "",
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "app": app.starlette_app,
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def test_load_content_returns_page_yaml() -> None:
    data = load_props("index")
    assert "page_content" in data
    assert data["page_content"]["hero"]["title"] == "Z8ter"


def test_render_returns_template_response() -> None:
    app = _prime_templates()
    request = _make_request(app)
    props = load_props("index")
    response = render(
        "pages/index.jinja",
        {
            "request": request,
            "page_id": "index",
            "title": "Demo",
            "page_content": props["page_content"],
        },
    )

    assert response.template.name == "pages/index.jinja"
    assert response.context["page_content"]["hero"]["title"] == "Z8ter"
