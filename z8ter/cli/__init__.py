"""CLI package compatibility exports.

Historically `z8ter.cli` duplicated app-directory helpers with stale path
conventions. Keep the public surface, but delegate to the canonical `z8ter`
module so CLI helpers and framework code stay in sync.
"""

from __future__ import annotations

from typing import Any

import z8ter as _z8ter

__version__ = _z8ter.__version__
get_app_dir = _z8ter.get_app_dir
get_templates = _z8ter.get_templates
set_app_dir = _z8ter.set_app_dir


def __getattr__(name: str) -> Any:
    """Delegate lazy path exports to the canonical `z8ter` module."""
    return getattr(_z8ter, name)


__all__ = ["__version__", "set_app_dir", "get_app_dir", "get_templates"]
