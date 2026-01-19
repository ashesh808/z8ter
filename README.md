# Z8ter

**Z8ter** is a lightweight, async Python web framework built on [Starlette](https://www.starlette.io/), designed for rapid development without compromising UX. It combines SSR-first rendering, auto-discovered routes, pluggable authentication, SQLite persistence, security middleware, and CLI tooling into one cohesive developer experience.

---

> **Status: Public Alpha** — Z8ter is under active development and not yet recommended for production. APIs may change without notice.

---

## Features

- **File-based Routing** — Views under `endpoints/views/` map to routes automatically
- **SSR + Islands** — Server-side rendering by default, with React "islands" for interactivity
- **Decorator-driven APIs** — Define REST APIs using decorators; auto-mounted under `/api/<name>`
- **Pluggable Auth** — Session middleware, Argon2 password hashing, and route guards like `@login_required`
- **SQLite Database** — Built-in SQLite persistence with session and user repositories
- **Security Middleware** — CSRF protection, rate limiting, security headers out of the box
- **Docker Ready** — Production-ready Dockerfile and docker-compose included
- **Health Checks** — Built-in `/health` endpoint for container orchestration
- **Composable Builder** — `AppBuilder` wires config, templating, Vite, sessions, and auth in order
- **CLI Tooling** — Scaffold projects, pages, APIs, and manage databases with `z8` commands
- **Modern Frontend** — Vite, React, TypeScript, Tailwind CSS, and DaisyUI ready out of the box

---

## Quickstart

```bash
# Create a new project
z8 new myapp
cd myapp

# Initialize database
z8 db init

# Install dependencies
uv sync              # Install Python dependencies
npm install          # Install Node dependencies

# Start the dev server
uv run z8 run dev
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
z8 db init
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

# With authentication support
pip install z8ter[auth]

# For development
pip install z8ter[dev]
```

---

## Project Structure

```
myapp/
├── main.py                 # Application entry point
├── .env                    # Environment configuration
├── Dockerfile              # Production container
├── docker-compose.yml      # Local development setup
├── data/                   # SQLite database (auto-created)
│   └── app.db
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

## Application Setup

### Basic Setup

```python
# main.py
import os
from z8ter.builders.app_builder import AppBuilder

DEBUG = os.getenv("Z8TER_DEBUG", "true").lower() == "true"

builder = AppBuilder()
builder.use_config(".env")
builder.use_templating()
builder.use_vite()
builder.use_errors()
builder.use_security_headers()
builder.use_health_check()

app = builder.build(debug=DEBUG)
asgi_app = app.starlette_app  # For uvicorn
```

### With Authentication and Database

```python
from z8ter.builders.app_builder import AppBuilder
from z8ter.database import Database, SQLiteSessionRepo, SQLiteUserRepo, init_database

# Initialize database
db = init_database()

# Create repositories
session_repo = SQLiteSessionRepo(db, secret_key=os.getenv("APP_SESSION_KEY"))
user_repo = SQLiteUserRepo(db)

builder = AppBuilder()
builder.use_config(".env")
builder.use_templating()
builder.use_vite()
builder.use_auth_repos(session_repo=session_repo, user_repo=user_repo)
builder.use_authentication()
builder.use_app_sessions()
builder.use_csrf()  # CSRF protection
builder.use_rate_limiting()  # Rate limiting
builder.use_security_headers()
builder.use_health_check()
builder.use_errors()

app = builder.build(debug=False)
```

---

## Database

Z8ter includes SQLite support with built-in session and user repositories.

### Initialize Database

```bash
# Using CLI
z8 db init

# Or in Python
from z8ter.database import init_database
db = init_database()
```

### Using Repositories

```python
from z8ter.database import Database, SQLiteUserRepo, SQLiteSessionRepo
from z8ter.auth.crypto import hash_password, verify_password

db = Database()  # Uses DATABASE_URL env or sqlite:///data/app.db

# User operations
user_repo = SQLiteUserRepo(db)
user = user_repo.create_user(
    email="user@example.com",
    password_hash=hash_password("secret123"),
    name="John Doe",
)

# Session operations
session_repo = SQLiteSessionRepo(db, secret_key="your-secret-key")
session_repo.insert(
    sid_plain="session-id",
    user_id=user["id"],
    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    remember=True,
    ip="127.0.0.1",
    user_agent="Mozilla/5.0",
)
```

### Database CLI Commands

```bash
z8 db init              # Initialize tables
z8 db status            # Show database info
z8 db reset --force     # Drop and recreate tables (destructive!)
```

---

## Security

Z8ter includes comprehensive security middleware.

### CSRF Protection

```python
builder.use_csrf()  # Enable CSRF middleware
```

In templates:
```html
<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <!-- form fields -->
</form>
```

### Rate Limiting

```python
builder.use_rate_limiting(
    requests_per_minute=60,
    burst_size=10,
    exempt_paths=["/health", "/static"],
)
```

### Security Headers

```python
builder.use_security_headers(
    enable_hsts=True,  # Only in production with HTTPS
    x_frame_options="DENY",
    content_security_policy="default-src 'self'",
)
```

### Input Validation

```python
from z8ter.security.validators import validate_email, validate_password

errors = []
if not validate_email(email):
    errors.append("Invalid email format")
if not validate_password(password, min_length=8):
    errors.append("Password must be at least 8 characters")
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

## Deployment

### Docker

```bash
# Build and run
docker build -t myapp .
docker run -p 8000:8000 -e Z8TER_DEBUG=false myapp

# Or with docker-compose
docker compose up
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `Z8TER_DEBUG` | Enable debug mode | `false` |
| `DATABASE_URL` | SQLite database URL | `sqlite:///data/app.db` |
| `APP_SESSION_KEY` | Secret key for sessions (32+ chars) | Required |
| `VITE_DEV_SERVER` | Vite dev server URL (dev only) | - |

### Health Check

The `/health` endpoint returns:
```json
{"status": "healthy", "version": "0.2.6"}
```

---

## Module Overview

| Module | Purpose |
|--------|---------|
| `z8ter.core` | ASGI wrapper around Starlette |
| `z8ter.endpoints` | Base `View` and `API` classes |
| `z8ter.builders` | `AppBuilder` and composable setup steps |
| `z8ter.auth` | Session management, crypto, guards, middleware |
| `z8ter.database` | SQLite persistence, session/user repositories |
| `z8ter.security` | CSRF, rate limiting, headers, validators |
| `z8ter.route_builders` | Auto-discovery of views and APIs |
| `z8ter.vite` | Vite asset integration (dev server + manifest) |
| `z8ter.cli` | CLI commands |
| `z8ter.config` | Environment-based configuration |
| `z8ter.errors` | Centralized error handling |

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `z8 new <name>` | Create a new project |
| `z8 create_page <name>` | Scaffold a page (view + template + content + TS) |
| `z8 create_api <name>` | Scaffold an API endpoint |
| `z8 run [dev\|prod\|LAN\|WAN]` | Run the server |
| `z8 db init` | Initialize database tables |
| `z8 db status` | Show database status |
| `z8 db reset` | Reset database (destructive) |

---

## Configuration Reference

### AppBuilder Methods

| Method | Description |
|--------|-------------|
| `use_config(env_file)` | Load environment configuration |
| `use_templating()` | Initialize Jinja2 templates |
| `use_vite()` | Enable Vite asset integration |
| `use_auth_repos(session_repo, user_repo)` | Register auth repositories |
| `use_authentication()` | Enable auth session middleware |
| `use_app_sessions()` | Enable application sessions |
| `use_csrf()` | Enable CSRF protection |
| `use_rate_limiting()` | Enable rate limiting |
| `use_security_headers()` | Add security headers |
| `use_health_check()` | Add /health endpoint |
| `use_errors()` | Register error handlers |
| `build(debug)` | Build the application |

---

## Requirements

- Python 3.10+
- Node.js 18+ (for frontend tooling)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
