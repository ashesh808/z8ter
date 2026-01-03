from __future__ import annotations

import z8ter
from z8ter.route_builders import (
    build_file_route,
    build_routes_from_apis,
    build_routes_from_pages,
)


def test_build_routes_from_pages_discovers_index_view() -> None:
    routes = build_routes_from_pages()
    assert any(route.endpoint.__name__ == "Index" for route in routes)
    assert any(route.path == "/" for route in routes)


def test_build_routes_from_apis_discovers_api_mounts() -> None:
    mounts = build_routes_from_apis()
    prefixes = {mount.path for mount in mounts}
    assert "/api/hello" in prefixes
    assert "/api/auth" in prefixes


def test_build_file_route_mounts_static_directory() -> None:
    mount = build_file_route()
    if z8ter.STATIC_PATH.exists():
        assert mount is not None
        assert mount.path == "/static"
    else:  # pragma: no cover - repository always ships static, but keep safety
        assert mount is None
