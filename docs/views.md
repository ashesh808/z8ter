# Views & Pages

Views combine Python handlers, Jinja templates, and optional structured page content to return server-rendered HTML.

## Create a page

From your generated project:

```bash
uv run z8 create_page hello
```

This creates a view, template, YAML content file, and TypeScript initializer. A small view is:

```python
# endpoints/views/hello.py
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import Response


class Hello(View):
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/hello.jinja", {
            "title": "Hello from Python."
        })
```

```jinja
{# templates/pages/hello.jinja #}
{% extends "base.jinja" %}
{% block content %}
  <h1>{{ title }}</h1>
  <p>A page built with Python.</p>
{% endblock %}
```

The default builder discovers this `View` subclass and serves it at `/hello`. Enable `use_templating()` in your builder; if the layout uses Vite tags, call `use_vite()` after templating.

## Routes and HTTP methods

```text
endpoints/views/index.py             → /
endpoints/views/about.py             → /about
endpoints/views/products/index.py    → /products
endpoints/views/products/detail.py   → /products/detail
```

Discovery happens when the app is built. Files without `View` subclasses are not page routes. Each view extends Starlette's `HTTPEndpoint`; define handlers such as `get`, `post`, `put`, `patch`, or `delete`. Unsupported methods return 405 rather than invoking an empty placeholder.

Override the inferred URL with a class-level `path`:

```python
from z8ter.endpoints.view import View


class ProductDetail(View):
    path = "/products/{product_id:int}"

    async def get(self, request):
        return self.render(request, "pages/product-detail.jinja", {
            "product_id": request.path_params["product_id"]
        })
```

Supply the referenced template. Starlette converters also support strings, floats, UUIDs, and paths containing slashes. Custom paths do not change `page_id` or the content file lookup.

Avoid duplicate route paths. Multiple view classes in one module can be disambiguated by appending the lowercase class name; explicit duplicate paths are not all registered. Prefer one view per file or unique explicit paths.

## Render context and content

`self.render(request, template_name, context=None)` returns a template response. It supplies:

- `request`: the current request.
- `page_id`: the view's module name with `endpoints.views.` removed.
- `page_content`: content loaded from the matching file.
- `csrf_token`: present when CSRF middleware has placed a token on request state.

For `endpoints.views.app.dashboard`, the page ID is `app.dashboard` and the loader checks `content/app/dashboard.json`, `.yaml`, then `.yml`. The first existing file wins. Missing content yields `{}`; invalid content raises an error. Use a mapping at the top level.

```yaml
# content/hello.yaml
headings:
  subheading: Welcome to the page
```

```jinja
<p>{{ page_content.headings.subheading }}</p>
```

Custom context is merged into the standard context, then the loader supplies `page_content`. Do not rely on passing your own `page_content` value to override that loader; use another context key for application data.

## Base layout and assets

The generated layout uses the **body** element's `data-page` attribute to select its TypeScript module:

```jinja
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}My app{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/output.css') }}">
</head>
<body data-page="{{ page_id }}">
  {% block content %}{% endblock %}
  {{ vite_script_tag("src/ts/app.ts") }}
</body>
</html>
```

`use_templating()` adds a `url_for` helper that accepts `filename` for static routes. `use_vite()` adds `vite_script_tag`; production needs the manifest created by `npm run build`. Jinja supports template inheritance, includes, and macros. Keep escaping enabled for untrusted values.

## Forms

Use a context manager to close any uploaded files, validate values, and return a response:

```python
# endpoints/views/contact.py
from z8ter.endpoints.view import View
from z8ter.responses import RedirectResponse


class Contact(View):
    async def get(self, request):
        return self.render(request, "pages/contact.jinja", {})

    async def post(self, request):
        async with request.form() as form:
            name = str(form.get("name", "")).strip()
        if not name:
            return self.render(request, "pages/contact.jinja", {
                "error": "Name is required"
            })
        # Persist or send the validated submission in your application.
        return RedirectResponse("/contact", status_code=303)
```

For a CSRF-protected form, include the token in its template:

```jinja
<form method="post">
  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
  <label>Name <input name="name" required></label>
  <button type="submit">Send</button>
</form>
```

CSRF must be enabled explicitly. It preserves form bodies for handlers, with an 8 MiB default limit for form-token requests. See [Security](security.md) for larger uploads and configuration.

## Requests, redirects, and errors

Read query parameters, headers, cookies, and path parameters from the request. Validate external values and account for `request.client` being `None`. Use async-compatible I/O or offload blocking calls to a thread pool.

For a fixed redirect, return `RedirectResponse("/new-page", status_code=303)` after a form POST. For login return URLs, use `z8ter.auth.guards.get_post_login_redirect()`; do not redirect to an unchecked `next` parameter.

Raise `starlette.exceptions.HTTPException(status_code=404, detail="Not found")` for missing resources. `builder.use_errors()` installs framework error handlers. Keep debug mode disabled in production.

## Protected views

```python
from z8ter.auth.guards import login_required
from z8ter.endpoints.view import View


class Dashboard(View):
    @login_required
    async def get(self, request):
        return self.render(request, "pages/dashboard.jinja", {
            "user": request.state.user
        })
```

This requires authentication repositories/middleware and `LOGIN_PATH` configuration. See [Authentication](authentication.md).

## Next steps

- [Interactive Islands](react-components.md)
- [API Endpoints](api-endpoints.md)
- [Project Structure](project-structure.md)
