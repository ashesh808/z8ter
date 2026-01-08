# z8ter/vite.py
"""Integration helpers for Vite-compiled frontend assets.

Supports two modes:
- Development: if VITE_DEV_SERVER env var is set, script tags load from dev server.
- Production: reads `manifest.json` from `static/js/.vite` to resolve asset URLs.

Caching:
- The manifest is cached in memory and reloaded if its mtime changes.
"""

import json
import os
from pathlib import Path

from markupsafe import Markup

import z8ter

# Optional dev server base URL, e.g., "http://localhost:5173".
VITE_DEV_SERVER = os.getenv("VITE_DEV_SERVER", "").rstrip("/")

# Internal manifest cache and last modified time.
_manifest_cache: dict[str, object] | None = None
_manifest_mtime: float | None = None


def _get_dist_path() -> Path:
    """Return the Vite dist directory path, resolved dynamically."""
    return z8ter.STATIC_PATH / "js" / ".vite"


def _load_manifest() -> dict:
    """Load and cache Vite manifest.json, reloading if the file changed.

    Returns:
        dict: Parsed manifest mapping entrypoints to asset metadata.

    Raises:
        FileNotFoundError: If manifest.json is missing in DIST.
        json.JSONDecodeError: If manifest.json is malformed.

    """
    global _manifest_cache, _manifest_mtime
    path = _get_dist_path() / "manifest.json"
    stat = path.stat()
    if _manifest_cache is None or _manifest_mtime != stat.st_mtime:
        _manifest_cache = json.loads(path.read_text())
        _manifest_mtime = stat.st_mtime
    return _manifest_cache  # type: ignore[return-value]


def vite_script_tag(entry: str) -> Markup:
    """Return <script> (and preload <link>) tags for a Vite entry.

    Args:
        entry: Entry filename as declared in Vite (e.g., "main.ts").

    Returns:
        Markup: HTML-safe tags (<script> and <link>) to include in templates.

    Raises:
        KeyError: If the requested entry is not in the manifest (prod mode).

    Notes:
        - In dev mode, bypasses manifest and always uses the dev server URL.
        - In prod mode, reads manifest.json and includes dependent imports/css.
        - Returned value is `Markup`, safe for direct injection into Jinja2.

    """
    # DEV SERVER MODE -------------------------------------------------
    if VITE_DEV_SERVER:
        return Markup(
            f'<script type="module" src="{VITE_DEV_SERVER}/{entry}"></script>'
        )

    # BUILD/MANIFEST MODE --------------------------------------------
    manifest = _load_manifest()
    if entry not in manifest:
        available = ", ".join(sorted(manifest.keys()))
        raise KeyError(
            f"Vite entry '{entry}' not found in manifest. Available: {available}"
        )

    item = manifest[entry]
    tags: list[str] = [
        f'<script type="module" src="/static/js/{item["file"]}"></script>'
    ]

    # Preload JS imports.
    for imp in item.get("imports", []):
        dep = manifest.get(imp)
        if dep and "file" in dep:
            tags.append(f'<link rel="modulepreload" href="/static/js/{dep["file"]}">')

    # Add CSS dependencies.
    for css in item.get("css", []):
        tags.append(f'<link rel="stylesheet" href="/static/js/{css}">')

    return Markup("\n".join(tags))
