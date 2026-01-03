# Z8ter

**Z8ter** is a lightweight, **async Python web framework** built on **Starlette**, designed for rapid development **without compromising UX**. It combines **SSR-first rendering**, **auto-discovered routes**, **auth scaffolding**, and **CLI tooling** into one cohesive developer experience.

---

> ⚠️ **Status: Public Alpha** — Z8ter is under active development and **not yet recommended for production**. APIs and module paths may change without notice.

---

## Quickstart

```bash
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

---

## Features

1. **File-based routing** — Files under `views/` map to routes automatically, each paired with a Jinja template and optional Python logic.
2. **SSR + Islands** — Server-side rendering by default, with per-page JS “islands” in `static/js/pages/<page_id>.js` for interactivity.
3. **Decorator-driven APIs** — Define class-based APIs using decorators; auto-mounted under `/api/<id>`.
4. **Auth & Guards** — Session middleware, Argon2 password hashing, and decorators like `@login_required` for route protection.
5. **Composed Builder** — `AppBuilder` wires config, templating, Vite, sessions, and error handling in a predictable order.
6. **CLI Tooling** — Scaffold apps, views, and APIs with `z8 new`, `z8 create_page`, `z8 create_api`; serve with `z8 run dev`.
7. **React, DaisyUI, Tailwind Ready** — Ships with modern frontend defaults for seamless full-stack workflows.

---

## Installation

```bash
# Using uv (recommended)
uv add z8ter

# Or using pip
pip install z8ter
```

---

## Authentication Example

```python
from z8ter.endpoints.view import View
from z8ter.auth.guards import login_required

class Dashboard(View):
    @login_required
    async def get(self, request):
        return self.render(request, "dashboard.jinja")
```

---

## AppBuilder Example

```python
from z8ter.builders.app_builder import AppBuilder
from myapp.repos import MySessionRepo, MyUserRepo

builder = AppBuilder()
builder.use_config(".env")
builder.use_templating()
builder.use_vite()
builder.use_app_sessions(secret_key="supersecret")
builder.use_auth_repos(session_repo=MySessionRepo(), user_repo=MyUserRepo())
builder.use_authentication()
builder.use_errors()

app = builder.build(debug=True)
```

---

## Module Overview

| Module                             | Purpose                                                                            |
| ---------------------------------- | ---------------------------------------------------------------------------------- |
| **`z8ter.auth`**                   | Auth contracts, Argon2 crypto, guards, and session middleware                      |
| **`z8ter.builders`**               | `AppBuilder` and composable setup steps for config, templating, vite, auth, errors |
| **`z8ter.cli`**                    | CLI entrypoints: `new`, `create_page`, `create_api`, and `run dev`                 |
| **`z8ter.endpoints`**              | Base `API` and `View` classes for SSR and REST endpoints                           |
| **`z8ter.route_builders`**         | Discovers SSR and API routes from filesystem                                       |
| **`z8ter.responses` / `requests`** | Wrappers around Starlette primitives                                               |
| **`z8ter.logging_utils`**          | Rich logging with `CancelledError` suppression                                     |
| **`z8ter.errors`**                 | Centralized 404/500 error handling                                                 |
| **`z8ter.vite`**                   | Dev/prod script tag helpers for Vite asset loading                                 |
| **`z8ter.config`**                 | Config loader with `BASE_DIR` and Starlette settings                               |
| **`z8ter.core`**                   | Lightweight ASGI wrapper around Starlette                                          |

---

## Framework Architecture

**Backend Flow**

- `route_builders` walks your project structure to register SSR `View` classes and API mounts.
- `View.render()` merges `content/*.yaml` data into Jinja templates, injecting `page_id` for client hydration.
- `API.endpoint()` decorators map handlers into Starlette routes automatically.
- Auth pipeline: `middleware → guards → session manager` ensures secure user sessions.
- Unified error and response modules abstract Starlette internals.

**Frontend Pipeline**

- `src/ts/app.ts` bootstraps JS “islands” using `data-page` attributes.
- Solid.js components (e.g. `z8-clock.tsx`) render inline via `solid-element` (no shadow DOM).
- `vite.config.ts` compiles and writes manifest under `/static/js/.vite`.
- `z8ter/vite.py` injects dev or manifest-based `<script>` tags dynamically.
- Tailwind and DaisyUI ship preconfigured for cohesive UI design.

**CLI & Scaffolding**

- `z8 new` → initializes a full project tree (safe for wheel installs).
- `z8 create_page` / `create_api` → generate views, content YAML, and JS islands.
- `z8 run dev` → launches Uvicorn with rich logging and live reload.

---

## Philosophy

> “Small surface area, sharp tools.”

- **SSR-first** with optional client interactivity
- **Conventions over configuration**
- **Predictable lifecycle**: builder → routes → middleware → templates
- **Full-stack parity** between Python and JS layers
