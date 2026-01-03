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

from importlib.resources import as_file, files

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    select_autoescape,
)

import z8ter


def _get_scaffold_path() -> str:
    """Get the path to the scaffold directory within the z8ter package."""
    scaffold_ref = files("z8ter").joinpath("scaffold")
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


def create_page(page_name: str) -> None:
    """Scaffold a new SSR page (view, template, content, and TS island).

    Generates:
        - views/{name}.py                       (server-side view)
        - templates/pages/{name}.jinja          (Jinja template)
        - content/{name}.yaml                   (optional content stub)
        - static/ts/pages/{name}.ts             (client-side island)

    Args:
        page_name: Logical page identifier (e.g., "about", "app/home").

    Behavior:
        - Capitalizes `page_name` for class names (simple heuristic).
        - Creates parent directories as needed.
        - Overwrites existing files only if paths already exist and you allow it
          via your VCS workflow (no interactive prompts here).

    Raises:
        jinja2.TemplateNotFound: if a required template is missing.
        OSError: on filesystem write issues.

    """
    class_name = page_name.capitalize()
    page_name_lower = page_name.lower()

    template_path = z8ter.TEMPLATES_DIR / "pages" / f"{page_name_lower}.jinja"
    view_path = z8ter.VIEWS_DIR / f"{page_name_lower}.py"
    ts_path = z8ter.TS_DIR / "pages" / f"{page_name_lower}.ts"
    content_path = z8ter.BASE_DIR / "content" / f"{page_name_lower}.yaml"

    data = {"class_name": class_name, "page_name_lower": page_name_lower}

    files = [
        ("create_page_templates/view.py.j2", view_path),
        ("create_page_templates/page.jinja.j2", template_path),
        ("create_page_templates/page.yaml.j2", content_path),
        ("create_page_templates/page.ts.j2", ts_path),
    ]

    for tpl_name, out_path in files:
        tpl = env.get_template(tpl_name)
        text = tpl.render(**data)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")


def create_api(api_name: str) -> None:
    """Scaffold a new API class under `api/`.

    Generates:
        - api/{name}.py

    Args:
        api_name: Logical API identifier (e.g., "hello", "billing").

    Behavior:
        - Capitalizes `api_name` for a class name (simple heuristic).
        - Creates parent directories as needed.

    Raises:
        jinja2.TemplateNotFound: if the API template is missing.
        OSError: on filesystem write issues.

    """
    api_name_lower = api_name.lower()
    class_name = api_name.capitalize()
    data = {"api_name_lower": api_name_lower, "class_name": class_name}

    api_path = z8ter.API_DIR / f"{api_name_lower}.py"

    tpl = env.get_template("create_api_template/api.py.j2")
    text = tpl.render(**data)

    api_path.parent.mkdir(parents=True, exist_ok=True)
    api_path.write_text(text, encoding="utf-8")
