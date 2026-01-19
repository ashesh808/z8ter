from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.routing import Route

from z8ter.builders import builder_functions as bf
from z8ter.core import Z8ter


async def _ping(request):
    return JSONResponse({"ok": True})


def _make_context() -> dict:
    routes = [Route("/ping", _ping, name="ping")]
    starlette_app = Starlette(routes=routes)
    app = Z8ter(debug=False, starlette_app=starlette_app)
    return {"app": app, "services": {}}


def test_use_config_builder_loads_env(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("APP_SESSION_KEY=thisisnotarealkey\n")
    ctx = _make_context()
    ctx["envfile"] = str(env_file)

    bf.use_config_builder(ctx)

    config = ctx["config"]
    assert callable(config)
    assert ctx["services"]["config"] is config
    assert config("APP_SESSION_KEY") == "thisisnotarealkey"


def test_use_templating_builder_sets_url_for_helper() -> None:
    ctx = _make_context()
    bf.use_templating_builder(ctx)
    templates = ctx["templates"]

    url_for = templates.env.globals["url_for"]
    assert url_for("ping") == "/ping"


def test_use_vite_builder_requires_templates() -> None:
    ctx = _make_context()
    with pytest.raises(RuntimeError):
        bf.use_vite_builder(ctx)

    bf.use_templating_builder(ctx)
    bf.use_vite_builder(ctx)
    templates = ctx["templates"]
    assert callable(templates.env.globals["vite_script_tag"])


def test_use_service_builder_inserts_and_replaces_services() -> None:
    ctx = _make_context()

    class ExampleService:
        pass

    first = ExampleService()
    ctx["obj"] = first
    bf.use_service_builder(ctx)
    assert ctx["services"]["exampleservice"] is first

    ctx["obj"] = ExampleService()
    with pytest.raises(RuntimeError):
        bf.use_service_builder(ctx)

    replacement = ExampleService()
    ctx.update({"obj": replacement, "replace": True})
    bf.use_service_builder(ctx)
    assert ctx["services"]["exampleservice"] is replacement


def test_publish_auth_repos_builder_registers_services() -> None:
    ctx = _make_context()

    class SessionRepo:
        def insert(self, **kwargs):  # pragma: no cover - helper
            raise NotImplementedError

        def revoke(self, **kwargs):
            return True

        def get_user_id(self, sid_plain: str) -> str | None:
            return "user-1"

    class UserRepo:
        def get_user_by_id(self, user_id: str):
            return {"id": user_id}

    ctx.update({"session_repo": SessionRepo(), "user_repo": UserRepo()})
    bf.publish_auth_repos_builder(ctx)

    services = ctx["services"]
    assert "session_repo" in services
    assert "user_repo" in services

    # Missing required methods should raise.
    ctx = _make_context()

    class BadSessionRepo:
        def get_user_id(self, sid_plain: str) -> str | None:
            return None

    ctx.update({"session_repo": BadSessionRepo(), "user_repo": UserRepo()})
    with pytest.raises(RuntimeError):
        bf.publish_auth_repos_builder(ctx)


def test_use_app_sessions_builder_configures_session_middleware() -> None:
    # Secret key must be at least 32 characters
    valid_key = "a" * 32

    ctx = _make_context()
    ctx["config"] = lambda key: {"APP_SESSION_KEY": valid_key}.get(key)
    bf.use_app_sessions_builder(ctx)

    middleware_classes = [
        m.cls.__name__ for m in ctx["app"].starlette_app.user_middleware
    ]
    assert "SessionMiddleware" in middleware_classes

    ctx = _make_context()
    ctx["secret_key"] = valid_key
    bf.use_app_sessions_builder(ctx)
    middleware_classes = [
        m.cls.__name__ for m in ctx["app"].starlette_app.user_middleware
    ]
    assert "SessionMiddleware" in middleware_classes

    # Test missing key raises TypeError
    ctx = _make_context()
    ctx["config"] = lambda key, default=None: None
    with pytest.raises(TypeError):
        bf.use_app_sessions_builder(ctx)

    # Test short key raises ValueError
    ctx = _make_context()
    ctx["secret_key"] = "too-short"
    with pytest.raises(ValueError):
        bf.use_app_sessions_builder(ctx)


def test_use_authentication_builder_adds_middleware_once() -> None:
    ctx = _make_context()
    bf.use_authentication_builder(ctx)
    bf.use_authentication_builder(ctx)

    middleware_classes = [
        m.cls.__name__ for m in ctx["app"].starlette_app.user_middleware
    ]
    assert middleware_classes.count("AuthSessionMiddleware") == 1


def test_use_errors_builder_registers_handlers() -> None:
    ctx = _make_context()
    bf.use_errors_builder(ctx)

    app = ctx["app"].starlette_app
    assert HTTPException in app.exception_handlers
    assert Exception in app.exception_handlers
