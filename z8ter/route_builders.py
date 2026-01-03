"""Route discovery for Z8ter.

This module scans your project for:
  - SSR Views: subclasses of `z8ter.endpoints.view.View`, creating `Route`s.
  - API classes: subclasses of `z8ter.endpoints.api.API`, creating `Mount`s.

It supports scanning either:
  - A Python package path (e.g., "endpoints.views", "endpoints.api"), or
  - A filesystem path (e.g., "endpoints/views", "endpoints/api").

Conventions:
- File-to-URL mapping:
    endpoints/resumes/index.py -> /resumes
    endpoints/resumes/edit.py  -> /resumes/edit
- A View subclass may override the inferred path via a class attribute `path`.
- If multiple View classes live in the same file with the same inferred URL,
  a stable disambiguation path is used: `/{base}/{cls.__name__.lower()}`.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import os
from collections.abc import Iterable
from pathlib import Path

from starlette.endpoints import HTTPEndpoint
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from z8ter.endpoints.api import API
from z8ter.endpoints.view import View

# ---------- helpers ----------


def _resolve_roots(pkg_or_path: str) -> tuple[str | None, list[str]]:
    """Resolve a package name or filesystem path into scan roots.

    If `pkg_or_path` is a Python package (e.g., "endpoints.views"), return
    `(pkg_name, [roots])` where `roots` are the package search locations.

    If it is a filesystem path (e.g., "endpoints/views" or "views"), return
    `(None, [abs_path])`.

    Args:
        pkg_or_path: Package or path string.

    Returns:
        Tuple of `(package_name_or_None, list_of_roots_as_strings)`.

    Raises:
        ModuleNotFoundError: If neither a package nor a folder can be located.

    """
    if os.path.sep in pkg_or_path or pkg_or_path.endswith(".py"):
        p = Path(pkg_or_path)
        if p.exists():
            return None, [str(p.resolve())]

    spec = importlib.util.find_spec(pkg_or_path)
    if spec and spec.submodule_search_locations:
        return pkg_or_path, list(spec.submodule_search_locations)

    p = Path(pkg_or_path)
    if p.exists():
        return None, [str(p.resolve())]

    raise ModuleNotFoundError(f"Cannot locate package or folder: {pkg_or_path!r}")


def _module_name_from_file(pkg_name: str, root: str, file_path: Path) -> str:
    """Compute a dotted module name from a package root + file path.

    Example:
        root="endpoints/views", file="endpoints/views/foo/bar.py"
        -> "endpoints.views.foo.bar"

    Args:
        pkg_name: Base package name (e.g., "endpoints.views").
        root: Root folder path that corresponds to `pkg_name`.
        file_path: Python file under the root.

    Returns:
        Dotted Python module path.

    """
    rel = file_path.relative_to(root)
    dotted = ".".join(rel.with_suffix("").parts)
    return f"{pkg_name}.{dotted}"


def _module_name_from_fs(file_path: Path) -> str:
    """Best-effort dotted module name relative to the current working directory.

    Assumes your project root (cwd) is on `sys.path`. This is typical when
    launching via `uvicorn --app-dir` or when the cwd is the project root.

    Args:
        file_path: Python file path under the project root.

    Returns:
        Dotted module path derived from the filesystem location.

    """
    rel = file_path.relative_to(Path().resolve())
    return ".".join(rel.with_suffix("").parts)


def _import_module_for(file_path: Path, pkg_name: str | None, root: str) -> object:
    """Import a module by computing its dotted path from file and root."""
    if pkg_name:
        mod_name = _module_name_from_file(pkg_name, root, file_path)
    else:
        mod_name = _module_name_from_fs(file_path)
    return importlib.import_module(mod_name)


def _iter_page_classes(mod) -> Iterable[type[HTTPEndpoint]]:
    """Yield subclasses of `View` (excluding the base class) from a module."""
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        if issubclass(obj, View) and obj is not View:
            yield obj


def _iter_api_classes(mod) -> Iterable[type[API]]:
    """Yield subclasses of `API` (excluding the base class) from a module."""
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        if issubclass(obj, API) and obj is not API:
            yield obj


def _url_from_file(root: Path, file_path: Path) -> str:
    """Map file location to a URL path.

    Rules:
        root/resumes/index.py -> /resumes
        root/resumes/edit.py  -> /resumes/edit

    Args:
        root: The scan root folder.
        file_path: The file for which to compute a URL.

    Returns:
        Clean URL path beginning with "/".

    """
    rel = file_path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1].lower() == "index":
        parts = parts[:-1]
    url = "/" + "/".join(parts)
    return url or "/"


# ---------- builders ----------


def build_routes_from_pages(pages_dir: str = "endpoints.views") -> list[Route]:
    """Discover and build routes for SSR pages (View subclasses).

    Scans a package (e.g., "endpoints.views") or folder ("endpoints/views") for
    subclasses of `View` and creates `Route` entries.

    Args:
        pages_dir: Package or path to scan for page classes.

    Returns:
        A list of Starlette `Route`s.

    Notes:
        - A View may define `path` to override the inferred URL.
        - If multiple View classes map to the same inferred URL, a disambiguated
          path is chosen: `/{base}/{cls.__name__.lower()}` (only when needed).

    """
    pkg_name, roots = _resolve_roots(pages_dir)
    routes: list[Route] = []
    seen_paths: set[str] = set()

    for root in roots:
        root_path = Path(root)
        for file_path in root_path.rglob("*.py"):
            if file_path.name == "__init__.py":
                continue
            mod = _import_module_for(file_path, pkg_name, root)
            classes = list(_iter_page_classes(mod))
            if not classes:
                continue
            base_path = _url_from_file(root_path, file_path)
            for cls in classes:
                path = getattr(cls, "path", None) or base_path
                if path in seen_paths and getattr(cls, "path", None) is None:
                    path = f"{base_path}/{cls.__name__.lower()}"
                if path not in seen_paths:
                    routes.append(Route(path, endpoint=cls))
                    seen_paths.add(path)
    return routes


def build_routes_from_apis(api_dir: str = "endpoints.api") -> list[Mount]:
    """Discover and build mounts for API classes.

    Scans a package (e.g., "endpoints.api") or folder ("endpoints/api") for
    subclasses of `API` and returns `Mount`s produced by `API.build_mount()`.

    Args:
        api_dir: Package or path to scan for API classes.

    Returns:
        A list of Starlette `Mount`s ready to be included in the app router.

    Notes:
        - This does not add a `/api` prefix by itself; composition happens in the
          higher-level builder.

    """
    pkg_name, roots = _resolve_roots(api_dir)
    mounts: list[Mount] = []
    for root in roots:
        root_path = Path(root)
        for file_path in root_path.rglob("*.py"):
            if file_path.name == "__init__.py":
                continue
            mod = _import_module_for(file_path, pkg_name, root)
            classes = list(_iter_api_classes(mod))
            if not classes:
                continue
            for cls in classes:
                mounts.append(cls.build_mount())
    return mounts


def build_file_route() -> Mount | None:
    """Mount `/static` if `STATIC_PATH` exists; return None otherwise.

    Returns:
        A Starlette `Mount` for static files or `None` if the path is absent.

    """
    import z8ter

    static_path = z8ter.STATIC_PATH
    if static_path and Path(static_path).exists():
        return Mount("/static", StaticFiles(directory=str(static_path)), name="static")
    return None
