# CLI Reference

Z8ter includes a command-line interface (CLI) for common development tasks like creating projects, scaffolding pages and APIs, and running the development server.

## Installation

The CLI is installed automatically with Z8ter:

```bash
pip install z8ter
```

Verify installation:

```bash
z8 --help
```

## Commands

### `z8 new` - Create New Project

Create a new Z8ter project from the template:

```bash
z8 new <project_name>
```

**Arguments:**
- `project_name`: Name of the project directory to create

**Example:**

```bash
z8 new myapp
cd myapp
```

This creates a complete project structure:

```
myapp/
├── .env
├── main.py
├── requirements.txt
├── package.json
├── vite.config.ts
├── tsconfig.json
├── endpoints/
│   ├── views/
│   │   └── index.py
│   └── api/
│       └── hello.py
├── templates/
│   ├── base.jinja
│   └── pages/
│       └── index.jinja
├── content/
│   └── index.yaml
├── static/
└── src/
    └── ts/
        ├── app.ts
        └── pages/
            └── index.ts
```

**Exit Codes:**
- `0`: Success
- `2`: Directory is not empty
- `3`: Template files not found
- `4`: Copy error

### `z8 create_page` - Scaffold a Page

Create a new SSR page with all associated files:

```bash
z8 create_page <name>
```

**Arguments:**
- `name`: Page name (can include path like `app/dashboard`)

**Examples:**

```bash
# Simple page
z8 create_page about

# Nested page
z8 create_page app/settings
z8 create_page admin/users/list
```

**Generated Files:**

For `z8 create_page products`:

```
endpoints/views/products.py      # View class
templates/pages/products.jinja   # Jinja template
content/products.yaml            # Page content
src/ts/pages/products.ts         # TypeScript module
```

**View Template:**

```python
# endpoints/views/products.py
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import Response


class Products(View):
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/products.jinja")
```

**Jinja Template:**

```jinja
{# templates/pages/products.jinja #}
{% extends "base.jinja" %}

{% block content %}
<main class="container mx-auto px-4 py-8">
    <h1>{{ page_content.title }}</h1>
</main>
{% endblock %}
```

**Content File:**

```yaml
# content/products.yaml
title: Products
```

**TypeScript Module:**

```typescript
// src/ts/pages/products.ts
interface PageCtx {
  pageId: string;
  id: string;
  body: HTMLElement;
}

export default function initProducts(ctx: PageCtx) {
  console.log('Products page initialized');
}
```

### `z8 create_api` - Scaffold an API

Create a new API endpoint class:

```bash
z8 create_api <name>
```

**Arguments:**
- `name`: API name (determines mount path)

**Examples:**

```bash
z8 create_api users
z8 create_api products
z8 create_api admin/reports
```

**Generated File:**

For `z8 create_api tasks`:

```python
# endpoints/api/tasks.py
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Tasks(API):
    @API.endpoint("GET", "/")
    async def list_tasks(self, request: Request):
        return JSONResponse({
            "ok": True,
            "data": []
        })

    @API.endpoint("GET", "/{id:int}")
    async def get_task(self, request: Request):
        task_id = request.path_params["id"]
        return JSONResponse({
            "ok": True,
            "data": {"id": task_id}
        })

    @API.endpoint("POST", "/")
    async def create_task(self, request: Request):
        data = await request.json()
        return JSONResponse({
            "ok": True,
            "data": data
        }, status_code=201)
```

### `z8 run` - Run Development Server

Start the application with Uvicorn:

```bash
z8 run [mode]
```

**Arguments:**
- `mode`: Server mode (optional, default: `dev`)

**Modes:**

| Mode | Host | Reload | Description |
|------|------|--------|-------------|
| `dev` | `127.0.0.1` | Yes | Local development with auto-reload |
| `prod` | `127.0.0.1` | No | Production mode, localhost only |
| `LAN` | LAN IP | Yes | Accessible from local network |
| `WAN` | `0.0.0.0` | No | Accessible from anywhere |

**Examples:**

```bash
# Development (default)
z8 run
z8 run dev

# Production
z8 run prod

# Network access (for testing on other devices)
z8 run LAN

# Public access (use with caution)
z8 run WAN
```

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Server port |
| `HOST` | varies by mode | Server host |

```bash
PORT=3000 z8 run dev
```

## Development Workflow

### 1. Create Project

```bash
z8 new myapp
cd myapp
```

### 2. Install Dependencies

```bash
# Python
pip install -r requirements.txt

# Node.js
npm install
```

### 3. Start Development Servers

**Terminal 1 - Python Server:**

```bash
z8 run dev
```

**Terminal 2 - Vite Dev Server (for HMR):**

```bash
npm run dev
```

Make sure `.env` has:

```env
VITE_DEV_SERVER=http://localhost:5173
```

### 4. Create Pages & APIs

```bash
# Create a new page
z8 create_page products

# Create an API
z8 create_api products
```

### 5. Build for Production

```bash
# Build frontend assets
npm run build

# Run in production mode
z8 run prod
```

## Scaffold Templates

The CLI uses Jinja2 templates stored in the package. Custom delimiters avoid conflicts:

- Variables: `[[ variable ]]`
- Blocks: `[% block %]`
- Comments: `[# comment #]`

### Custom Scaffold Directory

For local template customization, create `scaffold_dev/` in your project:

```
scaffold_dev/
├── create_page/
│   ├── view.py.jinja
│   ├── template.jinja.jinja
│   ├── content.yaml.jinja
│   └── ts.ts.jinja
└── create_api/
    └── api.py.jinja
```

The CLI checks `scaffold_dev/` first, then falls back to the package templates.

## Programmatic Usage

The CLI commands can also be used programmatically:

```python
from z8ter.cli.new import scaffold_project
from z8ter.cli.create import scaffold_page, scaffold_api

# Create project
result = scaffold_project("myapp")
if result == 0:
    print("Project created!")

# Scaffold page
scaffold_page("products")

# Scaffold API
scaffold_api("products")
```

## Troubleshooting

### Command Not Found

If `z8` is not found after installation:

```bash
# Check if it's in PATH
which z8

# Or use Python module directly
python -m z8ter.cli.main --help
```

### Permission Denied

```bash
# Use pip with user flag
pip install --user z8ter

# Or in a virtual environment
python -m venv venv
source venv/bin/activate
pip install z8ter
```

### Template Not Found

If scaffold templates are missing:

```bash
# Reinstall the package
pip install --force-reinstall z8ter
```

### Port Already in Use

```bash
# Use a different port
PORT=3000 z8 run dev

# Or find and kill the process
lsof -i :8000
kill <PID>
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `z8 new <name>` | Create new project |
| `z8 create_page <name>` | Scaffold SSR page |
| `z8 create_api <name>` | Scaffold API endpoint |
| `z8 run [mode]` | Run dev server |

## Next Steps

- [Getting Started](getting-started.md) - Create your first app
- [Views & Pages](views.md) - Understand page structure
- [API Endpoints](api-endpoints.md) - Build REST APIs
