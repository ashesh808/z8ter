"""Z8ter CLI scaffolding helpers.

This module provides simple code generators for pages and APIs using Jinja
templates. It renders files into your project's conventional directories
(`templates/pages`, `views`, `static/ts/pages`, `content`, and `api`).

Template resolution order (first match wins):
1) Local development overrides under `scaffold_dev/`
2) Built-in package templates under `z8ter/scaffold/`

Notes:
- Jinja delimiters are customized to avoid clashing with Jinja in Jinja
  (e.g., when generating `.jinja` files) and with TypeScript/HTML.

"""

import logging
from importlib.resources import as_file
from importlib.resources import files as resource_files
from pathlib import Path

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    select_autoescape,
)

import z8ter

logger = logging.getLogger("z8ter.cli")


def _to_pascal_case(name: str) -> str:
    """Convert a name to PascalCase.

    Examples:
        "about" -> "About"
        "user_profile" -> "UserProfile"
        "my-page" -> "MyPage"
    """
    # Split on underscores and hyphens
    parts = name.replace("-", "_").split("_")
    return "".join(word.capitalize() for word in parts)


def _get_scaffold_path() -> str:
    """Get the path to the scaffold directory within the z8ter package."""
    scaffold_ref = resource_files("z8ter").joinpath("scaffold")
    with as_file(scaffold_ref) as scaffold_path:
        return str(scaffold_path)


env = Environment(
    loader=ChoiceLoader(
        [
            FileSystemLoader("scaffold_dev"),
            FileSystemLoader(_get_scaffold_path()),
        ]
    ),
    autoescape=select_autoescape(
        enabled_extensions=(),
        default_for_string=False,
        default=False,
    ),
    variable_start_string="[[",
    variable_end_string="]]",
    block_start_string="[%",
    block_end_string="%]",
)


def create_page(page_name: str, *, force: bool = False) -> None:
    """Scaffold a new SSR page (view, template, content, and TS island).

    Generates:
        - views/{name}.py                       (server-side view)
        - templates/pages/{name}.jinja          (Jinja template)
        - content/{name}.yaml                   (optional content stub)
        - static/ts/pages/{name}.ts             (client-side island)

    Args:
        page_name: Logical page identifier (e.g., "about", "app/home").
        force: If True, overwrite existing files without warning.

    Behavior:
        - Converts `page_name` to PascalCase for class names (e.g., "user_profile" -> "UserProfile").
        - Creates parent directories as needed.
        - Skips existing files unless force=True, logging a warning.

    Raises:
        jinja2.TemplateNotFound: if a required template is missing.
        OSError: on filesystem write issues.

    """
    class_name = _to_pascal_case(page_name)
    page_name_lower = page_name.lower().replace("-", "_")

    template_path = z8ter.TEMPLATES_DIR / "pages" / f"{page_name_lower}.jinja"
    view_path = z8ter.VIEWS_DIR / f"{page_name_lower}.py"
    ts_path = z8ter.TS_DIR / "pages" / f"{page_name_lower}.ts"
    content_path = z8ter.BASE_DIR / "content" / f"{page_name_lower}.yaml"

    data = {"class_name": class_name, "page_name_lower": page_name_lower}

    file_mappings = [
        ("create_page_templates/view.py.j2", view_path),
        ("create_page_templates/page.jinja.j2", template_path),
        ("create_page_templates/page.yaml.j2", content_path),
        ("create_page_templates/page.ts.j2", ts_path),
    ]

    for tpl_name, out_path in file_mappings:
        # Check if file exists
        if out_path.exists() and not force:
            logger.warning("Skipping %s (already exists, use --force to overwrite)", out_path)
            continue

        tpl = env.get_template(tpl_name)
        text = tpl.render(**data)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        logger.info("Created %s", out_path)


def create_api(api_name: str, *, force: bool = False) -> None:
    """Scaffold a new API class under `api/`.

    Generates:
        - api/{name}.py

    Args:
        api_name: Logical API identifier (e.g., "hello", "billing").
        force: If True, overwrite existing files without warning.

    Behavior:
        - Converts `api_name` to PascalCase for class names (e.g., "user_data" -> "UserData").
        - Creates parent directories as needed.
        - Skips existing files unless force=True, logging a warning.

    Raises:
        jinja2.TemplateNotFound: if the API template is missing.
        OSError: on filesystem write issues.

    """
    api_name_lower = api_name.lower().replace("-", "_")
    class_name = _to_pascal_case(api_name)
    data = {"api_name_lower": api_name_lower, "class_name": class_name}

    api_path = z8ter.API_DIR / f"{api_name_lower}.py"

    # Check if file exists
    if api_path.exists() and not force:
        logger.warning("Skipping %s (already exists, use --force to overwrite)", api_path)
        return

    tpl = env.get_template("create_api_template/api.py.j2")
    text = tpl.render(**data)

    api_path.parent.mkdir(parents=True, exist_ok=True)
    api_path.write_text(text, encoding="utf-8")
    logger.info("Created %s", api_path)
