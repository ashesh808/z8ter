# Getting Started

This guide will help you create your first Z8ter application in minutes.

## Prerequisites

- Python 3.10 or higher
- Node.js 18+ (for frontend tooling)
- pip (Python package manager)

## Installation

Install Z8ter using pip:

```bash
pip install z8ter
```

For development dependencies:

```bash
pip install z8ter[dev]
```

## Creating a New Project

The fastest way to get started is using the CLI:

```bash
z8 new myapp
cd myapp
```

This creates a new project with the following structure:

```
myapp/
├── .env                    # Environment variables
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── package.json            # Node.js dependencies
├── vite.config.ts          # Vite configuration
├── tsconfig.json           # TypeScript configuration
├── endpoints/
│   ├── views/              # SSR page views
│   │   └── index.py
│   └── api/                # API endpoints
│       └── hello.py
├── templates/
│   ├── base.jinja          # Base template
│   └── pages/
│       └── index.jinja
├── content/
│   └── index.yaml          # Page content
├── static/                 # Static assets
└── src/
    └── ts/                 # TypeScript/React code
        ├── app.ts
        └── pages/
            └── index.ts
```

## Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies (for frontend)
npm install
```

## Running the Development Server

Start the development server:

```bash
z8 run dev
```

Your app is now running at `http://localhost:8000`.

The dev server includes:
- **Hot reload**: Python changes restart the server automatically
- **Vite HMR**: Frontend changes update instantly without page refresh

## Your First Page

Let's create a new page. Use the CLI:

```bash
z8 create_page about
```

This generates:
- `endpoints/views/about.py` - The view class
- `templates/pages/about.jinja` - The template
- `content/about.yaml` - Page content
- `src/ts/pages/about.ts` - TypeScript module

### The View (`endpoints/views/about.py`)

```python
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import Response


class About(View):
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/about.jinja")
```

### The Template (`templates/pages/about.jinja`)

```jinja
{% extends "base.jinja" %}

{% block content %}
<main class="container mx-auto px-4 py-8">
    <h1 class="text-4xl font-bold">{{ page_content.title }}</h1>
    <p class="mt-4">{{ page_content.description }}</p>
</main>
{% endblock %}
```

### The Content (`content/about.yaml`)

```yaml
title: About Us
description: Learn more about our company and mission.
```

Visit `http://localhost:8000/about` to see your new page!

## Your First API Endpoint

Create an API endpoint:

```bash
z8 create_api users
```

This generates `endpoints/api/users.py`:

```python
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Users(API):
    @API.endpoint("GET", "/")
    async def list_users(self, request: Request):
        return JSONResponse({
            "ok": True,
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ]
        })

    @API.endpoint("GET", "/{user_id:int}")
    async def get_user(self, request: Request):
        user_id = request.path_params["user_id"]
        return JSONResponse({
            "ok": True,
            "user": {"id": user_id, "name": "Alice"}
        })

    @API.endpoint("POST", "/")
    async def create_user(self, request: Request):
        data = await request.json()
        return JSONResponse({
            "ok": True,
            "user": {"id": 3, "name": data.get("name")}
        }, status_code=201)
```

Access your API at:
- `GET http://localhost:8000/api/users/`
- `GET http://localhost:8000/api/users/1`
- `POST http://localhost:8000/api/users/`

## Understanding the Entry Point

Your `main.py` configures the application:

```python
from z8ter.builders.app_builder import AppBuilder

# Create the builder
builder = AppBuilder()

# Configure features
builder.use_config(".env")      # Load environment variables
builder.use_templating()        # Enable Jinja2 templates
builder.use_vite()              # Enable Vite asset handling
builder.use_errors()            # Register error handlers

# Build the application
app = builder.build(debug=True)
```

The builder pattern lets you compose features as needed. Add authentication, custom services, and more by chaining builder methods.

## Running in Production

Build frontend assets:

```bash
npm run build
```

Run in production mode:

```bash
z8 run prod
```

Or use uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Next Steps

- [Project Structure](project-structure.md) - Understand the file layout
- [Views & Pages](views.md) - Deep dive into SSR pages
- [API Endpoints](api-endpoints.md) - Build REST APIs
- [React Components](react-components.md) - Add interactive UI
- [Authentication](authentication.md) - Secure your app
