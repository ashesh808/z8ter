"""Z8ter framework package root.

Provides:
- Version info (`__version__`).
- App directory management (`set_app_dir`, `get_app_dir`).
- Centralized project path resolution (views, templates, static, api, ts).
- Cached Jinja2 template environment (`get_templates`).
- Lazy attributes (PEP 562) for common paths and templates.

Conventions:
- App root precedence: explicit `set_app_dir(...)` > env `Z8TER_APP_DIR` > cwd().
- Paths assume the standard Z8ter layout:
    <base>/
      endpoints/views/
      endpoints/api/
      templates/
      static/
      src/ts/
"""

from __future__ import annotations

# --- enable pkgutil-style namespace so plugins can add subpackages ---
from pkgutil import extend_path  # noqa: E402

__path__ = extend_path(__path__, __name__)  # noqa: E402
# --------------------------------------------------------------------

__version__ = "0.2.6"

import contextvars
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from starlette.templating import Jinja2Templates

# -------- App directory registry (explicit > env > cwd) --------

# Context-local explicit app directory. If unset, fallback is env or cwd.
_APP_DIR: contextvars.ContextVar[Path | None] = contextvars.ContextVar(
    "Z8TER_APP_DIR_EXPLICIT", default=None
)

# Thread-safe lock for cache operations (RLock allows reentrant acquisition
# since get_templates() calls _current_paths() while holding the lock)
_cache_lock = threading.RLock()


def set_app_dir(path: str | Path) -> None:
    """Set the application root directory.

    Args:
        path: Absolute or relative path to the project root.

    Notes:
        - Updates a context-local value, so different contexts may override it.
        - Clears caches so subsequent lookups reflect the new base.

    """
    p = Path(path).resolve()
    _APP_DIR.set(p)
    _clear_cache()


def get_app_dir() -> Path:
    """Resolve the current application root directory.

    Precedence:
        1) explicit via `set_app_dir(...)`
        2) env var `Z8TER_APP_DIR`
        3) `Path.cwd()`

    Returns:
        Absolute `Path` to the app root.

    """
    explicit = _APP_DIR.get()
    if explicit is not None:
        return explicit
    env = os.getenv("Z8TER_APP_DIR")
    return Path(env).resolve() if env else Path.cwd().resolve()


# -------- Path resolution (single source of truth) --------


@dataclass(frozen=True)
class Paths:
    """Resolved project paths derived from the app base directory."""

    base: Path
    views: Path
    templates: Path
    static: Path
    api: Path
    ts: Path


def _resolve_paths(base: Path) -> Paths:
    """Compute all derived paths from a base directory."""
    base = base.resolve()
    return Paths(
        base=base,
        views=base / "endpoints" / "views",
        templates=base / "templates",
        static=base / "static",
        api=base / "endpoints" / "api",
        ts=base / "src" / "ts",
    )


_paths_cache: Paths | None = None


def _current_paths() -> Paths:
    """Return cached paths for the current app dir; recompute on base change.

    Thread-safe: uses a lock to prevent race conditions during cache updates.
    """
    global _paths_cache
    base = get_app_dir()

    # Fast path: check cache without lock
    cached = _paths_cache
    if cached is not None and cached.base == base:
        return cached

    # Slow path: acquire lock and update cache
    with _cache_lock:
        # Double-check after acquiring lock
        if _paths_cache is None or _paths_cache.base != base:
            _paths_cache = _resolve_paths(base)
        return _paths_cache


def _clear_cache() -> None:
    """Clear cached paths and template environment (called on base change).

    Thread-safe: uses a lock to prevent race conditions.
    """
    global _paths_cache, _templates_cache
    with _cache_lock:
        _paths_cache = None
        _templates_cache = None


# -------- Lazy module attributes (PEP 562) --------

_templates_cache: Jinja2Templates | None = None


def get_templates() -> Jinja2Templates:
    """Return a cached `Jinja2Templates` bound to the current templates dir.

    The cache is invalidated automatically when `set_app_dir(...)` updates the
    base directory.

    Thread-safe: uses a lock to prevent race conditions during cache updates.

    Returns:
        A `Jinja2Templates` instance rooted at the resolved templates folder.

    """
    global _templates_cache

    # Fast path: check cache without lock
    if _templates_cache is not None:
        return _templates_cache

    # Slow path: acquire lock and create templates
    with _cache_lock:
        # Double-check after acquiring lock
        if _templates_cache is None:
            tdir = _current_paths().templates
            _templates_cache = Jinja2Templates(directory=str(tdir))
        return _templates_cache


# Pre-defined attribute names for lazy access (avoids dict creation on each call)
_PATH_ATTRS = frozenset(
    {"BASE_DIR", "VIEWS_DIR", "TEMPLATES_DIR", "STATIC_PATH", "API_DIR", "TS_DIR"}
)


def __getattr__(name: str) -> Any:
    """Expose common path aliases and `templates` lazily.

    Supported names:
        - "BASE_DIR", "VIEWS_DIR", "TEMPLATES_DIR", "STATIC_PATH",
          "API_DIR", "TS_DIR": return `Path` objects.
        - "templates": return `Jinja2Templates` (same as `get_templates()`).

    Raises:
        AttributeError: If the attribute is not recognized.

    Performance:
        Uses a pre-defined set for attribute lookup instead of creating a dict
        on every access.

    """
    if name == "templates":
        return get_templates()

    if name not in _PATH_ATTRS:
        raise AttributeError(f"module 'z8ter' has no attribute {name!r}")

    # Only compute paths when actually needed
    paths = _current_paths()
    if name == "BASE_DIR":
        return paths.base
    if name == "VIEWS_DIR":
        return paths.views
    if name == "TEMPLATES_DIR":
        return paths.templates
    if name == "STATIC_PATH":
        return paths.static
    if name == "API_DIR":
        return paths.api
    if name == "TS_DIR":
        return paths.ts

    raise AttributeError(f"module 'z8ter' has no attribute {name!r}")


__all__ = ["__version__", "set_app_dir", "get_app_dir", "get_templates"]
