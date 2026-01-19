"""Endpoint utilities for rendering templates and loading page content.

This module provides helpers to:
  - Render a Jinja template into a Starlette `Response`.
  - Load structured YAML content for a page, keyed by `page_id`.

Conventions:
  - Content files live under BASE_DIR/content/{page_id}.yaml.
  - Templates are resolved via the app's Jinja2 environment.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml
from starlette.templating import Jinja2Templates

import z8ter
from z8ter.responses import Response

logger = logging.getLogger("z8ter")


def _get_contents_path() -> Path:
    """Return the content directory path, resolved dynamically."""
    return z8ter.BASE_DIR / "content"


def render(template_name: str, context: dict[str, Any] | None = None) -> Response:
    """Render a Jinja template into a Starlette `TemplateResponse`.

    Args:
        template_name: Path to the Jinja template, relative to templates dir.
        context: Template context variables. Must include 'request' key.

    Returns:
        Response: A Starlette TemplateResponse object.

    Notes:
        - The context MUST contain a 'request' key with the current Request object.
        - Response type is framework-specific but generally behaves like ASGI.

    """
    templates: Jinja2Templates = z8ter.get_templates()
    ctx = context or {}
    request = ctx.get("request")
    if request is not None:
        # Use new Starlette API: TemplateResponse(request, name, context)
        return templates.TemplateResponse(request, template_name, ctx)
    # Fallback for tests without request (will trigger deprecation warning)
    return templates.TemplateResponse(template_name, ctx)


def load_props(page_id: str, base: Path | None = None) -> dict[str, Any]:
    """Load page props for a given page id from content files.

    - Supports .json, .yaml, .yml (first match wins).
    - `page_id` may use dots or slashes: "app.home" -> "app/home".

    Args:
        page_id: Identifier like "about" or "app.home".
        base: Optional override for the content root (defaults to content path).

    Returns:
        {"page_content": <mapping>}

    Raises:
        json.JSONDecodeError / yaml.YAMLError: If content is malformed.

    """
    root = base if base is not None else _get_contents_path()
    rel = page_id.replace(".", "/")

    candidates = [
        root / f"{rel}.json",
        root / f"{rel}.yaml",
        root / f"{rel}.yml",
    ]

    # Find existing content files
    found_files = [path for path in candidates if path.is_file()]

    if not found_files:
        logger.warning("No content found for '%s' under %s", page_id, root)
        return {"page_content": {}}

    # Warn if multiple content files exist
    if len(found_files) > 1:
        logger.warning(
            "Multiple content files found for '%s': %s. Using first match: %s",
            page_id,
            [str(f) for f in found_files],
            found_files[0],
        )

    # Use first match
    path = found_files[0]
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)

    return {"page_content": dict(data) if data else {}}
