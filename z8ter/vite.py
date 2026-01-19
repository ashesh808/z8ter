# z8ter/vite.py
"""Integration helpers for Vite-compiled frontend assets.

Supports two modes:
- Development: if VITE_DEV_SERVER env var is set, script tags load from dev server.
- Production: reads `manifest.json` from `static/js/.vite` to resolve asset URLs.

Caching:
- The manifest is cached in memory and reloaded if its mtime or size changes.
- Cache can also be invalidated based on file content hash for reliability.

Environment variables:
- VITE_DEV_SERVER: Base URL for Vite dev server (e.g., "http://localhost:5173")
- VITE_ALWAYS_RELOAD_MANIFEST: If "true", skip caching in prod (for debugging)
"""

import hashlib
import json
import logging
import os
import threading
from pathlib import Path

from markupsafe import Markup

import z8ter

logger = logging.getLogger("z8ter.vite")

# Optional dev server base URL, e.g., "http://localhost:5173".
VITE_DEV_SERVER = os.getenv("VITE_DEV_SERVER", "").rstrip("/")

# Debug option to always reload manifest
ALWAYS_RELOAD_MANIFEST = os.getenv("VITE_ALWAYS_RELOAD_MANIFEST", "").lower() == "true"

# Internal manifest cache with mtime and hash for reliable invalidation
_manifest_cache: dict[str, object] | None = None
_manifest_mtime: float | None = None
_manifest_size: int | None = None
_manifest_lock = threading.Lock()


def _get_dist_path() -> Path:
    """Return the Vite dist directory path, resolved dynamically."""
    return z8ter.STATIC_PATH / "js" / ".vite"


def _load_manifest() -> dict:
    """Load and cache Vite manifest.json, reloading if the file changed.

    Uses both mtime and file size for cache invalidation, which is more reliable
    in containerized environments where mtime may not change on file replacement.

    Returns:
        dict: Parsed manifest mapping entrypoints to asset metadata.

    Raises:
        FileNotFoundError: If manifest.json is missing in DIST.
        json.JSONDecodeError: If manifest.json is malformed.

    """
    global _manifest_cache, _manifest_mtime, _manifest_size

    path = _get_dist_path() / "manifest.json"
    stat = path.stat()

    # Check if we need to reload (mtime or size changed)
    needs_reload = (
        ALWAYS_RELOAD_MANIFEST
        or _manifest_cache is None
        or _manifest_mtime != stat.st_mtime
        or _manifest_size != stat.st_size
    )

    if needs_reload:
        with _manifest_lock:
            # Double-check after acquiring lock
            if (
                ALWAYS_RELOAD_MANIFEST
                or _manifest_cache is None
                or _manifest_mtime != stat.st_mtime
                or _manifest_size != stat.st_size
            ):
                _manifest_cache = json.loads(path.read_text())
                _manifest_mtime = stat.st_mtime
                _manifest_size = stat.st_size

    return _manifest_cache  # type: ignore[return-value]


def vite_script_tag(entry: str, *, fallback_to_manifest: bool = True) -> Markup:
    """Return <script> (and preload <link>) tags for a Vite entry.

    Args:
        entry: Entry filename as declared in Vite (e.g., "main.ts").
        fallback_to_manifest: If True and dev server is configured but manifest
                              exists, fall back to manifest on dev server errors.

    Returns:
        Markup: HTML-safe tags (<script> and <link>) to include in templates.

    Raises:
        KeyError: If the requested entry is not in the manifest (prod mode).
        FileNotFoundError: If manifest.json is missing and not in dev mode.

    Notes:
        - In dev mode, bypasses manifest and uses the dev server URL.
        - In prod mode, reads manifest.json and includes dependent imports/css.
        - If VITE_DEV_SERVER is set but manifest exists, we use the dev server.
          If the dev server is down, the browser will show errors for those assets.
        - Returned value is `Markup`, safe for direct injection into Jinja2.

    """
    # DEV SERVER MODE -------------------------------------------------
    if VITE_DEV_SERVER:
        # Log that we're using dev server
        logger.debug("Using Vite dev server for entry: %s", entry)
        return Markup(
            f'<script type="module" src="{VITE_DEV_SERVER}/{entry}"></script>'
        )

    # BUILD/MANIFEST MODE --------------------------------------------
    try:
        manifest = _load_manifest()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Vite manifest.json not found at {_get_dist_path() / 'manifest.json'}. "
            "Run 'npm run build' or set VITE_DEV_SERVER for development mode."
        )

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
