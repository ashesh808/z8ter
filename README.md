# Z8ter

**Z8ter** is a lightweight, async Python web framework built on [Starlette](https://www.starlette.io/), designed for rapid development without compromising UX. It combines SSR-first rendering, auto-discovered routes, pluggable authentication, and CLI tooling into one cohesive developer experience.

---

> **Status: Public Alpha** — Z8ter is under active development and not yet recommended for production. APIs may change without notice.

---

## Features

- **File-based Routing** — Views under `endpoints/views/` map to routes automatically
- **SSR + Islands** — Server-side rendering by default, with React "islands" for interactivity
- **Decorator-driven APIs** — Define REST APIs using decorators; auto-mounted under `/api/<name>`
- **Pluggable Auth** — Session middleware, Argon2 password hashing, and route guards like `@login_required`
- **Composable Builder** — `AppBuilder` wires config, templating, Vite, sessions, and auth in order
- **CLI Tooling** — Scaffold projects, pages, and APIs with `z8 new`, `z8 create_page`, `z8 create_api`
- **Modern Frontend** — Vite, React, TypeScript, Tailwind CSS, and DaisyUI ready out of the box

---

## Quickstart

```bash
# Create a new project
z8 new myapp
cd myapp
uv sync              # Install Python dependencies
npm install          # Install Node dependencies
uv run z8 run dev    # Start the dev server
```

<details>
<summary>Alternative: Using pip instead of uv</summary>

```bash
z8 new myapp
cd myapp
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
z8 run dev
```
</details>

Visit `http://localhost:8000` to see your app.

---

## Installation

```bash
# Using uv (recommended)
uv add z8ter

# Or using pip
pip install z8ter
```

For development dependencies:

```bash
pip install z8ter[dev]
```

---

## Project Structure

```
myapp/
├── main.py                 # Application entry point
├── .env                    # Environment configuration
├── endpoints/
│   ├── views/              # SSR page views → URLs
│   │   ├── index.py        # → /
│   │   └── about.py        # → /about
│   └── api/                # REST API endpoints
│       └── hello.py        # → /api/hello/*
├── templates/              # Jinja2 templates
│   ├── base.jinja
│   └── pages/
├── content/                # YAML page content
├── static/                 # Static assets
└── src/ts/                 # TypeScript/React code
    ├── app.ts
    └── ui-components/      # React Web Components
```

---

## Creating Pages

```bash
z8 create_page products
```

```python
# endpoints/views/products.py
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import Response


class Products(View):
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/products.jinja")
```

---

## Creating APIs

```bash
z8 create_api users
```

```python
# endpoints/api/users.py
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Users(API):
    @API.endpoint("GET", "/")
    async def list_users(self, request: Request):
        return JSONResponse({"ok": True, "users": []})

    @API.endpoint("GET", "/{user_id:int}")
    async def get_user(self, request: Request):
        user_id = request.path_params["user_id"]
        return JSONResponse({"ok": True, "user": {"id": user_id}})
```

---

## Application Setup

```python
# main.py
from z8ter.builders.app_builder import AppBuilder

builder = AppBuilder()
builder.use_config(".env")
builder.use_templating()
builder.use_vite()
builder.use_errors()

app = builder.build(debug=True)
```

### With Authentication

```python
from z8ter.builders.app_builder import AppBuilder
from app.repos import SessionRepo, UserRepo

builder = AppBuilder()
builder.use_config(".env")
builder.use_templating()
builder.use_vite()
builder.use_auth_repos(session_repo=SessionRepo(), user_repo=UserRepo())
builder.use_authentication()
builder.use_app_sessions()
builder.use_errors()

app = builder.build(debug=True)
```

---

## Protected Routes

```python
from z8ter.endpoints.view import View
from z8ter.auth.guards import login_required


class Dashboard(View):
    @login_required
    async def get(self, request):
        user = request.state.user
        return self.render(request, "pages/dashboard.jinja", {"user": user})
```

---

## Module Overview

| Module                 | Purpose                                                 |
| ---------------------- | ------------------------------------------------------- |
| `z8ter.core`           | ASGI wrapper around Starlette                           |
| `z8ter.endpoints`      | Base `View` and `API` classes                           |
| `z8ter.builders`       | `AppBuilder` and composable setup steps                 |
| `z8ter.auth`           | Session management, crypto, guards, middleware          |
| `z8ter.route_builders` | Auto-discovery of views and APIs                        |
| `z8ter.vite`           | Vite asset integration (dev server + manifest)          |
| `z8ter.cli`            | CLI commands: `new`, `create_page`, `create_api`, `run` |
| `z8ter.config`         | Environment-based configuration                         |
| `z8ter.errors`         | Centralized error handling                              |

---

## CLI Commands

| Command                        | Description                                      |
| ------------------------------ | ------------------------------------------------ |
| `z8 new <name>`                | Create a new project                             |
| `z8 create_page <name>`        | Scaffold a page (view + template + content + TS) |
| `z8 create_api <name>`         | Scaffold an API endpoint                         |
| `z8 run [dev\|prod\|LAN\|WAN]` | Run the server                                   |

---

## Documentation

Full documentation is available in the [`docs/`](docs/) folder:

- [Getting Started](docs/getting-started.md)
- [Project Structure](docs/project-structure.md)
- [Views & Pages](docs/views.md)
- [API Endpoints](docs/api-endpoints.md)
- [React Components](docs/react-components.md)
- [Authentication](docs/authentication.md)
- [Configuration](docs/configuration.md)
- [CLI Reference](docs/cli.md)

---

## Requirements

- Python 3.10+
- Node.js 18+ (for frontend tooling)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
