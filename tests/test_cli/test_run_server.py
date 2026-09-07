"""Cover CLI loading of generated apps and legacy builder-only projects."""

import os
import sys
from types import ModuleType

import pytest
import uvicorn
from starlette.testclient import TestClient

import z8ter
from z8ter.builders.app_builder import AppBuilder
from z8ter.cli.new import new_project
from z8ter.cli.run_server import load_app, run_server


@pytest.mark.parametrize("mode", ["dev", "prod"])
def test_generated_app_keeps_middleware_and_health_route(
    tmp_path, monkeypatch, mode
):
    """Load the actual scaffold through the factory selected by each CLI mode."""
    new_project("generated", path=str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "main", raising=False)
    monkeypatch.delenv("Z8TER_APP_FACTORY", raising=False)
    monkeypatch.delenv("Z8TER_DEBUG", raising=False)
    z8ter.set_app_dir(tmp_path)

    def inspect_worker(app_factory, **kwargs):
        config = uvicorn.Config(
            app_factory, factory=kwargs["factory"], log_config=None
        )
        config.load()
        with TestClient(config.loaded_app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.headers["x-content-type-options"] == "nosniff"
        assert sys.modules["main"].app.debug is (mode == "dev")

    monkeypatch.setattr(uvicorn, "run", inspect_worker)
    try:
        run_server(mode=mode)
    finally:
        sys.modules.pop("main", None)


def test_load_app_supports_legacy_builder_only_projects(monkeypatch):
    """Keep older projects working when no app has been built at import time."""
    module = ModuleType("main")
    module.app_builder = AppBuilder()
    module.app_builder.use_health_check()
    monkeypatch.setitem(sys.modules, "main", module)

    with TestClient(load_app()) as client:
        assert client.get("/health").status_code == 200


def test_load_app_reuses_app_without_asgi_alias(monkeypatch):
    """Reuse a built Z8ter app even without the optional ASGI alias."""
    module = ModuleType("main")
    builder = AppBuilder()
    builder.use_health_check()
    module.app = builder.build()
    module.app_builder = builder
    monkeypatch.setitem(sys.modules, "main", module)

    assert load_app() is module.app


def test_explicit_factory_and_debug_override_are_preserved(monkeypatch):
    """Respect application-specific factory and debug settings."""
    captured = {}
    monkeypatch.setenv("Z8TER_APP_FACTORY", "custom:create_app")
    monkeypatch.setenv("Z8TER_DEBUG", "false")

    def capture_worker(app_factory, **kwargs):
        captured["app_factory"] = app_factory
        captured.update(kwargs)

    monkeypatch.setattr(uvicorn, "run", capture_worker)
    run_server(mode="dev")

    assert captured["app_factory"] == "custom:create_app"
    assert captured["reload"] is True
    assert os.environ["Z8TER_DEBUG"] == "false"
