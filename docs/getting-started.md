# Getting Started

Create a Z8ter app, build its browser assets, and run the server and asset watchers together. The Z8ter 0.3.1 starter uses Python and Jinja for pages, with Solid and TypeScript for interactive components.

## Prerequisites

- Python 3.10 or higher
- Node.js 22.12 or higher and npm
- [uv](https://docs.astral.sh/uv/getting-started/installation/), or pip in a Python virtual environment

## Create and Run an App with uv

Run these commands in order, starting in the directory where you want to create your project:

```bash
# 1. Create your app
uvx --from z8ter z8 new myapp

# 2. Install the Python and frontend dependencies
cd myapp
uv sync
npm install

# 3. Build the CSS, JavaScript, and Vite manifest
npm run build

# 4. Start the server and both asset watchers
uv run npm run dev
```

`uvx` runs the scaffolding CLI without a global installation. `uv sync` creates the project's Python environment from `pyproject.toml`. Running npm through `uv run` makes the project's `z8` command available to the server process.

Keep the terminal open. Once the server and asset watchers are ready, open [http://127.0.0.1:8000](http://127.0.0.1:8000). The starter also includes an [about page](http://127.0.0.1:8000/about) and a [hello API](http://127.0.0.1:8000/api/hello/).

## Alternative: pip

Create a virtual environment beside the new project and keep it active throughout setup. On macOS or Linux:

```bash
# 1. Create an environment, install the CLI, and scaffold the app
python3 -m venv .z8ter-env
source .z8ter-env/bin/activate
python -m pip install z8ter
z8 new myapp

# 2. Install the project dependencies in the active environment
cd myapp
python -m pip install -r requirements.txt
npm install

# 3. Build the browser assets
npm run build

# 4. Start the server and asset watchers
npm run dev
```

On Windows PowerShell, use `python` instead of `python3` and activate the environment with `.z8ter-env\Scripts\Activate.ps1` instead of the `source` command.

When returning to a pip project in a new terminal, activate that environment again before running `z8` or `npm run dev`.

## Updating an Existing Project

Z8ter 0.3.1 requires Starlette 1.6 or newer within the 1.x series (`>=1.6,<2`). If an older project's requirements pin Starlette 0.x, remove that stale pin and let Z8ter select its supported dependency range. Review any direct Starlette usage in your own application when upgrading.

For a uv project, update the locked Z8ter dependency:

```bash
uv sync --upgrade-package z8ter
```

For pip, update the dependencies in your active environment:

```bash
python -m pip install --upgrade -r requirements.txt
```

Updating the Python package does not replace your application's scaffold files. Review the current starter's frontend dependencies and scripts separately, then rebuild assets and run your app's checks.

## What the Development Command Runs

`npm run dev` starts three processes:

- **Python server:** `z8 run dev` serves the app and reloads after Python changes.
- **CSS watcher:** Tailwind writes `static/css/output.css` as templates and component classes change.
- **JavaScript watcher:** Vite rebuilds TypeScript/Solid bundles and `static/js/.vite/manifest.json`.

The starter uses Vite's build watcher. Refresh your browser after frontend changes. `z8 run dev` by itself starts only the Python server; it does not compile CSS or JavaScript.

No database or authentication setup is needed for the starter's home page and sample API. Add these features when your application needs them; see [Authentication](authentication.md) and [Security](security.md).

## Project Structure

The generated project's main files are:

```text
myapp/
├── main.py                 # AppBuilder configuration and ASGI app
├── pyproject.toml          # Python project dependencies for uv
├── requirements.txt        # Python dependencies for pip
├── package.json            # Frontend dependencies and scripts
├── vite.config.ts          # Vite build configuration
├── tsconfig.json           # TypeScript configuration
├── endpoints/
│   ├── views/
│   │   ├── index.py        # Home page
│   │   └── about.py        # About page
│   └── api/
│       └── hello.py        # Sample JSON API
├── templates/
│   ├── base.jinja          # Layout and Vite script tag
│   └── pages/
│       ├── index.jinja
│       └── about.jinja
├── content/
│   └── index.yaml          # Home-page content
├── static/                 # Favicons and built browser assets
└── src/
    ├── css/app.css         # Tailwind and DaisyUI entry
    └── ts/
        ├── app.ts          # Per-page module loader
        ├── pages/          # Page initialization modules
        └── ui-components/  # Solid custom elements
```

Create a `.env` file when you need application configuration; see [Configuration](configuration.md).

## Your First Page

The starter already has an about page. Create a new products page from another terminal in the project directory:

```bash
uv run z8 create_page products
```

For pip, activate your environment and run `z8 create_page products`. The CLI generates:

- `endpoints/views/products.py` — the view class
- `templates/pages/products.jinja` — the template
- `content/products.yaml` — page content
- `src/ts/pages/products.ts` — the page's TypeScript module

Edit those files to show your own content. For example:

### The View (`endpoints/views/products.py`)

```python
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import Response


class Products(View):
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/products.jinja")
```

### The Template (`templates/pages/products.jinja`)

```jinja
{% extends "base.jinja" %}

{% block content %}
<section class="card bg-base-200">
    <div class="card-body">
        <h1 class="text-4xl font-bold">{{ page_content.title }}</h1>
        <p class="mt-4">{{ page_content.description }}</p>
    </div>
</section>
{% endblock %}
```

### The Content (`content/products.yaml`)

```yaml
title: Our Products
description: Explore what we are building.
```

With the development watchers running, open [http://127.0.0.1:8000/products](http://127.0.0.1:8000/products) after the new assets finish building.

## Your First API Endpoint

Create an API scaffold:

```bash
uv run z8 create_api users
```

For pip, use `z8 create_api users` in your active environment. This creates `endpoints/api/users.py`. Replace its example handler with the following to return some sample data:

```python
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Users(API):
    @API.endpoint("GET", "/")
    async def list_users(self, request: Request) -> JSONResponse:
        return JSONResponse({
            "ok": True,
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ],
        })

    @API.endpoint("GET", "/{user_id:int}")
    async def get_user(self, request: Request) -> JSONResponse:
        user_id = request.path_params["user_id"]
        return JSONResponse({
            "ok": True,
            "user": {"id": user_id, "name": "Alice"},
        })

    @API.endpoint("POST", "/")
    async def create_user(self, request: Request) -> JSONResponse:
        data = await request.json()
        return JSONResponse({
            "ok": True,
            "user": {"id": 3, "name": data.get("name")},
        }, status_code=201)
```

These handlers return demonstration data; the POST handler does not persist a user. Access them at:

- `GET http://127.0.0.1:8000/api/users/`
- `GET http://127.0.0.1:8000/api/users/1`
- `POST http://127.0.0.1:8000/api/users/`

## Understanding the Entry Point

The generated `main.py` exposes the configured `app` and its `asgi_app` alias. The Z8ter CLI reuses that configured app. Its configuration follows this pattern:

```python
import os

from z8ter.builders.app_builder import AppBuilder

app_builder = AppBuilder()
app_builder.use_config(".env")
app_builder.use_templating()
app_builder.use_vite()
app_builder.use_errors()
app_builder.use_security_headers()
app_builder.use_health_check()

app = app_builder.build(
    debug=os.getenv("Z8TER_DEBUG", "true").lower() == "true"
)
```

Builder methods register the integrations you choose. Authentication, sessions, CSRF protection, and rate limiting need explicit configuration; they are not all enabled by creating a starter project.

## Running in Production

Build frontend assets before starting the production server:

```bash
npm run typecheck
npm run build
```

Set `Z8TER_DEBUG=false` in your deployment environment. Then run the generated ASGI app without reload:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

For pip, run `uvicorn main:app --host 0.0.0.0 --port 8000` with the project's environment active. Deploy behind your usual ASGI reverse proxy.

## Next Steps

- [Project Structure](project-structure.md) — Understand the file layout
- [Views & Pages](views.md) — Create server-rendered pages
- [API Endpoints](api-endpoints.md) — Build JSON APIs
- [Interactive Islands](react-components.md) — Add Solid custom elements and page-specific browser behavior
- [Authentication](authentication.md) — Configure user authentication
