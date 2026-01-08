# Project Structure

Z8ter uses a convention-based project structure that keeps your code organized and enables automatic route discovery.

## Standard Layout

```
myapp/
├── .env                        # Environment configuration
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── package.json                # Node.js dependencies
├── vite.config.ts              # Vite build configuration
├── tsconfig.json               # TypeScript configuration
│
├── endpoints/                  # HTTP endpoint handlers
│   ├── views/                  # SSR page views
│   │   ├── __init__.py
│   │   ├── index.py            # → /
│   │   ├── about.py            # → /about
│   │   ├── login.py            # → /login
│   │   └── app/                # Nested routes
│   │       ├── __init__.py
│   │       └── dashboard.py    # → /app/dashboard
│   │
│   └── api/                    # REST API endpoints
│       ├── __init__.py
│       ├── hello.py            # → /api/hello/*
│       ├── users.py            # → /api/users/*
│       └── auth.py             # → /api/auth/*
│
├── templates/                  # Jinja2 templates
│   ├── base.jinja              # Base layout template
│   ├── pages/                  # Page-specific templates
│   │   ├── index.jinja
│   │   ├── about.jinja
│   │   └── app/
│   │       └── dashboard.jinja
│   └── server-components/      # Reusable template components
│       ├── general.jinja
│       └── islands.jinja
│
├── content/                    # YAML/JSON page content
│   ├── index.yaml
│   ├── about.yaml
│   └── app/
│       └── dashboard.yaml
│
├── static/                     # Static assets (served at /static)
│   ├── favicon/
│   ├── css/
│   └── js/                     # Vite build output
│       └── .vite/
│           └── manifest.json
│
├── src/                        # Frontend source code
│   ├── css/
│   │   └── app.css             # Tailwind/CSS entry
│   └── ts/
│       ├── app.ts              # TypeScript entry point
│       ├── pages/              # Page-specific JS modules
│       │   ├── common.ts
│       │   ├── index.ts
│       │   └── app/
│       │       └── dashboard.ts
│       ├── ui-components/      # React Web Components
│       │   ├── z8-clock.tsx
│       │   └── z8-theme-toggle.tsx
│       └── utils/              # Shared utilities
│           └── theme.ts
│
└── app/                        # Application logic (optional)
    ├── identity/               # Domain: user identity
    │   ├── adapter/            # Repository implementations
    │   │   ├── session_repo.py
    │   │   └── user_repo.py
    │   └── usecases/           # Business logic
    │       ├── manage_sessions.py
    │       └── manage_users.py
    └── billing/                # Domain: billing
        └── ...
```

## Directory Details

### `/endpoints/views/`

Server-side rendered page views. Each Python file becomes a route:

| File | URL |
|------|-----|
| `index.py` | `/` |
| `about.py` | `/about` |
| `login.py` | `/login` |
| `app/dashboard.py` | `/app/dashboard` |

Files named `index.py` map to the parent directory's URL.

### `/endpoints/api/`

REST API endpoints. Each file creates an API mount:

| File | Base URL |
|------|----------|
| `hello.py` | `/api/hello` |
| `users.py` | `/api/users` |
| `auth.py` | `/api/auth` |

Individual routes within the API class extend from this base.

### `/templates/`

Jinja2 templates for rendering HTML:

- `base.jinja`: The root template that others extend
- `pages/`: Page-specific templates, mirroring the views structure
- `server-components/`: Reusable template fragments (macros, includes)

### `/content/`

Structured content for pages in YAML or JSON format:

```yaml
# content/about.yaml
title: About Us
hero:
  heading: Our Story
  subheading: Building the future of web development
sections:
  - title: Our Mission
    content: ...
```

Content is automatically loaded and available as `page_content` in templates.

### `/static/`

Static files served at `/static/`. Includes:

- Favicon files
- Pre-built CSS
- Vite build output (`/js/.vite/manifest.json`)
- Images and other assets

### `/src/`

Frontend source code processed by Vite:

- `ts/app.ts`: Main entry point, handles page module loading
- `ts/pages/`: Page-specific TypeScript (loaded based on `data-page` attribute)
- `ts/ui-components/`: React components wrapped as Web Components
- `css/app.css`: Tailwind CSS entry point

### `/app/` (Optional)

Business logic organized by domain. This follows clean architecture principles:

- `adapter/`: Repository implementations (database, external services)
- `usecases/`: Business logic and use cases

## File Naming Conventions

### Views

| Pattern | Example | URL |
|---------|---------|-----|
| `{name}.py` | `about.py` | `/about` |
| `index.py` | `users/index.py` | `/users` |
| `{name}.py` in subdir | `users/profile.py` | `/users/profile` |

### Templates

Templates should mirror the view structure:
- View: `endpoints/views/about.py`
- Template: `templates/pages/about.jinja`

### Content

Content files should match the `page_id`:
- View module: `endpoints.views.about`
- Content: `content/about.yaml`

## Path Resolution

Z8ter resolves paths based on the app directory:

```python
import z8ter

# Set app directory explicitly
z8ter.set_app_dir("/path/to/myapp")

# Or rely on defaults:
# 1. Explicit set_app_dir()
# 2. Z8TER_APP_DIR environment variable
# 3. Current working directory

# Access resolved paths
print(z8ter.BASE_DIR)       # /path/to/myapp
print(z8ter.VIEWS_DIR)      # /path/to/myapp/endpoints/views
print(z8ter.TEMPLATES_DIR)  # /path/to/myapp/templates
print(z8ter.STATIC_PATH)    # /path/to/myapp/static
print(z8ter.API_DIR)        # /path/to/myapp/endpoints/api
print(z8ter.TS_DIR)         # /path/to/myapp/src/ts
```

## Customizing Structure

While Z8ter works best with conventions, you can customize paths:

```python
from z8ter.route_builders import build_routes_from_pages, build_routes_from_apis

# Use custom view directory
routes = build_routes_from_pages("myviews")  # Package name
routes = build_routes_from_pages("src/views")  # Filesystem path

# Use custom API directory
mounts = build_routes_from_apis("myapis")
```

## Next Steps

- [Views & Pages](views.md) - Create SSR pages
- [API Endpoints](api-endpoints.md) - Build REST APIs
- [React Components](react-components.md) - Add interactive elements
