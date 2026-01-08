from __future__ import annotations

import sys
from pathlib import Path

import pytest

import z8ter


@pytest.fixture(autouse=True)
def repo_app_dir() -> Path:
    """Ensure tests resolve paths against the repository sample app.

    The project ships a demo application under z8ter-app/ (templates,
    endpoints, content, etc.). Many utilities rely on `z8ter.get_app_dir()`
    to locate those assets, so we point the resolver at the z8ter-app
    directory for every test run.
    """
    previous = z8ter.get_app_dir()
    base = Path(__file__).resolve().parent.parent / "z8ter-app"
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    z8ter.set_app_dir(base)
    try:
        yield base
    finally:
        z8ter.set_app_dir(previous)
