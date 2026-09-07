"""Regression coverage for CSRF-protected form submissions."""

import asyncio

import pytest
from starlette.applications import Starlette
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from z8ter.security.csrf import CSRFMiddleware


@pytest.fixture
def client():
    async def form_endpoint(request):
        if request.method == "GET":
            return JSONResponse({"csrf_token": request.state.csrf_token})
        async with request.form() as form:
            result = {"name": form.get("name")}
            if "upload" in form:
                result["upload"] = (await form["upload"].read()).decode()
        return JSONResponse(result)

    app = Starlette(routes=[Route("/form", form_endpoint, methods=["GET", "POST"])])
    app.add_middleware(
        CSRFMiddleware,
        secret_key="test-secret",
        cookie_secure=False,
        max_form_body_size=1024,
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("multipart", [False, True])
@pytest.mark.parametrize("token_in_header", [False, True])
def test_valid_form_reaches_handler_with_body_intact(
    client, multipart, token_in_header
):
    token = client.get("/form").json()["csrf_token"]
    data = {"name": "Ada"}
    headers = {}
    if token_in_header:
        headers["X-CSRF-Token"] = token
    else:
        data["csrf_token"] = token
    files = {"upload": ("example.txt", b"hello", "text/plain")} if multipart else None

    response = client.post("/form", data=data, files=files, headers=headers)

    assert response.status_code == 200
    expected = {"name": "Ada"}
    if multipart:
        expected["upload"] = "hello"
    assert response.json() == expected


@pytest.mark.parametrize("token", [None, "invalid"])
def test_missing_or_invalid_form_token_is_rejected(client, token):
    client.get("/form")
    data = {"name": "Ada"}
    if token is not None:
        data["csrf_token"] = token

    response = client.post("/form", data=data)

    assert response.status_code == 403


@pytest.mark.parametrize("content_length", [None, b"1", b"10240"])
def test_oversize_chunked_form_is_rejected_before_buffering_all_chunks(
    client, content_length
):
    headers = [(b"content-type", b"multipart/form-data; boundary=example")]
    if content_length is not None:
        headers.append((b"content-length", content_length))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/form",
        "raw_path": b"/form",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    chunks_read = 0
    messages = []

    async def receive():
        nonlocal chunks_read
        chunks_read += 1
        return {
            "type": "http.request",
            "body": b"x" * 512,
            "more_body": chunks_read < 20,
        }

    async def send(message):
        messages.append(message)

    asyncio.run(client.app(scope, receive, send))

    assert messages[0]["status"] == 413
    assert chunks_read <= 3


def test_header_token_upload_does_not_use_form_buffer_limit(client):
    token = client.get("/form").json()["csrf_token"]
    response = client.post(
        "/form",
        headers={"X-CSRF-Token": token},
        data={"name": "Ada"},
        files={"upload": ("large.txt", b"x" * 2048, "text/plain")},
    )

    assert response.status_code == 200
    assert response.json() == {"name": "Ada", "upload": "x" * 2048}


def test_stricter_application_body_limit_is_preserved(client):
    with TestClient(
        RequestBodyLimitMiddleware(client.app, max_body_size=128)
    ) as limited:
        response = limited.post("/form", data={"name": "x" * 256})

    assert response.status_code == 413


def test_builder_applies_custom_form_body_limit():
    from z8ter.builders.app_builder import AppBuilder

    builder = AppBuilder()
    builder.use_config()
    builder.use_csrf(secret_key="test-secret", max_form_body_size=128)
    app = builder.build(debug=False)
    with TestClient(app.starlette_app) as client:
        response = client.post("/form", data={"name": "x" * 256})

    assert response.status_code == 413
