"""Lightweight API base class with a decorator-based endpoint registry.

Usage:
    # api/hello.py
    from z8ter.endpoints.api import API

    class Hello(API):
        @API.endpoint("GET", "/hello")
        async def hello(self, request):
            return {"ok": True}

Discovery & mounting:
- Subclasses defined under modules starting with `api.` derive an API id from
  their module path: `api.billing.invoices -> "billing/invoices"`.
- `build_mount()` returns a Starlette `Mount` with the class's registered routes.
- At the app level, a route builder typically mounts these under a common
  prefix (e.g., `/api`). This class does *not* add `/api` automatically.

Contract:
- Decorate instance methods with `@API.endpoint(method, path)`.
- Methods are invoked on a shared instance created by `build_mount()`.

Important limitations:
- A single instance is shared across all routes. Do NOT store request-specific
  state on `self` as it will leak between requests. Use `request.state` instead.
- For per-request isolation, create dependencies via constructor arguments rather
  than storing state on the instance.

Caveats:
- `build_mount()` adds a leading slash to the mount prefix if missing.
- Legacy: A leading `"endpoints"` segment is trimmed from the derived id for
  backwards compatibility. New projects should place APIs under `api/` directly.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from starlette.routing import Mount, Route


class API:
    """Base class for decorator-driven API endpoint registration.

    Subclass this in `api/...` modules and decorate methods with `@API.endpoint`
    to expose HTTP routes. A subclass's endpoints are collected at import time
    via `__init_subclass__` and later turned into a `Mount` by `build_mount()`.

    Class Attributes:
        _api_id: Derived from the module path (e.g., "billing/invoices").
        _endpoints: Collected list of (method, subpath, func_name) tuples.

    Important:
        All routes share a single instance of the API class. Do NOT store
        request-specific state on `self` - it will leak between requests.
        Use `request.state` for per-request data instead.

    """

    _api_id: ClassVar[str]
    _endpoints: ClassVar[list[tuple[str, str, str]]]

    def __init_subclass__(cls: type[API], **kwargs: Any) -> None:
        """Collect endpoint metadata and derive a stable API id.

        Derivation rules:
            - If module starts with "api.", strip that prefix and replace dots
              with slashes to form the id.
            - Otherwise, use the module as-is and replace dots with slashes.

        Also scans class dict for attributes tagged by `@API.endpoint` and
        records them in `_endpoints`.
        """
        super().__init_subclass__(**kwargs)
        mod: str = cls.__module__
        if mod.startswith("api."):
            api_id = mod.removeprefix("api.")
        else:
            api_id = mod
        cls._api_id = api_id.replace(".", "/")
        cls._endpoints = []
        for name, obj in cls.__dict__.items():
            meta: tuple[str, str] | None = getattr(obj, "_z8_endpoint", None)
            if meta:
                http_method, subpath = meta
                cls._endpoints.append((http_method, subpath, name))

    @classmethod
    def build_mount(cls: type[API]) -> Mount:
        """Create a Starlette `Mount` containing all registered routes.

        The mount prefix is the derived `_api_id`, with a defensive leading `/`
        added if missing.

        Returns:
            starlette.routing.Mount: mount wrapping each declared endpoint.

        Notes:
            - Higher-level builders often mount this under a shared prefix
              (e.g., `/api`). Avoid hardcoding `/api` here to keep layering
              clean and let builders decide composition.
            - All routes share a single instance. Do not store request state on self.

        Legacy behavior:
            A leading "endpoints" segment is trimmed from the prefix for backwards
            compatibility with older project structures. New projects should place
            API modules directly under `api/`.

        """
        # Legacy: trim "endpoints" prefix for backwards compatibility
        prefix: str = f"{cls._api_id}".removeprefix("endpoints")
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"

        # Create a single instance shared across all routes
        # WARNING: Do not store request-specific state on self
        inst: API = cls()
        routes: list[Route] = [
            Route(subpath, endpoint=getattr(inst, func_name), methods=[method])
            for (method, subpath, func_name) in getattr(cls, "_endpoints", [])
        ]
        return Mount(prefix, routes=routes)

    @staticmethod
    def endpoint(
        method: str, path: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a handler as an HTTP endpoint.

        Args:
            method: HTTP verb (e.g., "GET", "POST").
            path: Subpath for this endpoint (e.g., "/hello").

        Returns:
            The original function, tagged with endpoint metadata.

        Example:
            @API.endpoint("GET", "/ping")
            async def ping(self, request): return {"ok": True}

        """

        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            fn._z8_endpoint = method.upper(), path  # type: ignore[attr-defined]
            return fn

        return deco
