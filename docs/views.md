# Views & Pages

Views in Z8ter are server-side rendered (SSR) pages. They combine Python logic, Jinja2 templates, and structured content to deliver complete HTML pages.

## Creating a View

### Using the CLI

The easiest way to create a view:

```bash
z8 create_page products
```

This generates:
- `endpoints/views/products.py`
- `templates/pages/products.jinja`
- `content/products.yaml`
- `src/ts/pages/products.ts`

### Manual Creation

Create `endpoints/views/products.py`:

```python
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import Response


class Products(View):
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/products.jinja")
```

## The View Class

Views extend `z8ter.endpoints.view.View`, which itself extends Starlette's `HTTPEndpoint`.

### Basic Structure

```python
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import Response


class MyPage(View):
    # Optional: override the default URL path
    path = "/custom-url"

    async def get(self, request: Request) -> Response:
        """Handle GET requests"""
        return self.render(request, "pages/mypage.jinja")

    async def post(self, request: Request) -> Response:
        """Handle POST requests"""
        form_data = await request.form()
        # Process form...
        return self.render(request, "pages/mypage.jinja", {
            "message": "Form submitted!"
        })
```

### HTTP Methods

Views support all HTTP methods:

```python
class ResourcePage(View):
    async def get(self, request: Request) -> Response:
        """Retrieve and display"""
        pass

    async def post(self, request: Request) -> Response:
        """Create new resource"""
        pass

    async def put(self, request: Request) -> Response:
        """Update resource"""
        pass

    async def delete(self, request: Request) -> Response:
        """Delete resource"""
        pass
```

## Rendering Templates

The `render()` method combines templates with context:

```python
def render(
    self,
    request: Request,
    template_name: str,
    context: dict = None
) -> Response
```

### Automatic Context

The `render()` method automatically injects:

- `request`: The current HTTP request
- `page_id`: Derived from the view's module path
- `page_content`: Loaded from the matching content file

```python
class About(View):
    async def get(self, request: Request) -> Response:
        # page_id = "about" (from endpoints.views.about)
        # page_content = loaded from content/about.yaml
        return self.render(request, "pages/about.jinja")
```

### Custom Context

Add your own context variables:

```python
class Products(View):
    async def get(self, request: Request) -> Response:
        products = await fetch_products()

        return self.render(request, "pages/products.jinja", {
            "products": products,
            "total_count": len(products),
            "categories": ["Electronics", "Books", "Clothing"]
        })
```

## URL Routing

### Automatic Routes

File location determines the URL:

| File | URL |
|------|-----|
| `endpoints/views/index.py` | `/` |
| `endpoints/views/about.py` | `/about` |
| `endpoints/views/products.py` | `/products` |
| `endpoints/views/products/index.py` | `/products` |
| `endpoints/views/products/detail.py` | `/products/detail` |
| `endpoints/views/app/dashboard.py` | `/app/dashboard` |

### Custom Paths

Override the automatic path with the `path` attribute:

```python
class ProductDetail(View):
    path = "/products/{product_id:int}"

    async def get(self, request: Request) -> Response:
        product_id = request.path_params["product_id"]
        product = await get_product(product_id)
        return self.render(request, "pages/product-detail.jinja", {
            "product": product
        })
```

### Path Parameters

Use Starlette's path parameter syntax:

```python
# String parameter (default)
path = "/users/{username}"

# Integer parameter
path = "/products/{id:int}"

# Float parameter
path = "/coordinates/{lat:float}/{lon:float}"

# Path parameter (matches slashes)
path = "/files/{filepath:path}"
```

Access parameters via `request.path_params`:

```python
async def get(self, request: Request) -> Response:
    username = request.path_params["username"]
    # ...
```

## Page Content

Content files provide structured data for templates.

### Content File (`content/about.yaml`)

```yaml
title: About Our Company
hero:
  heading: Building the Future
  subheading: Innovation meets simplicity
  cta:
    label: Learn More
    href: "#mission"

team:
  - name: Alice Johnson
    role: CEO
    bio: Visionary leader with 20 years of experience.
  - name: Bob Smith
    role: CTO
    bio: Tech innovator and open source advocate.

sections:
  mission:
    title: Our Mission
    content: |
      We believe in creating tools that empower developers
      to build amazing experiences.
```

### Using Content in Templates

```jinja
{% extends "base.jinja" %}

{% block content %}
<section class="hero">
    <h1>{{ page_content.hero.heading }}</h1>
    <p>{{ page_content.hero.subheading }}</p>
    <a href="{{ page_content.hero.cta.href }}">
        {{ page_content.hero.cta.label }}
    </a>
</section>

<section class="team">
    {% for member in page_content.team %}
    <div class="team-member">
        <h3>{{ member.name }}</h3>
        <p class="role">{{ member.role }}</p>
        <p>{{ member.bio }}</p>
    </div>
    {% endfor %}
</section>
{% endblock %}
```

### JSON Content

You can also use JSON:

```json
{
  "title": "About Us",
  "hero": {
    "heading": "Building the Future"
  }
}
```

Z8ter checks for files in order: `.json`, `.yaml`, `.yml`

## Templates

### Base Template

Create a base template that others extend:

```jinja
{# templates/base.jinja #}
<!DOCTYPE html>
<html lang="en" data-page="{{ page_id }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ page_content.title | default('My App') }}{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">
</head>
<body>
    {% block header %}
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
        </nav>
    </header>
    {% endblock %}

    <main>
        {% block content %}{% endblock %}
    </main>

    {% block footer %}
    <footer>
        <p>&copy; 2024 My App</p>
    </footer>
    {% endblock %}

    {{ vite_script_tag("src/ts/app.ts") }}
</body>
</html>
```

### Page Template

```jinja
{# templates/pages/products.jinja #}
{% extends "base.jinja" %}

{% block title %}Products - {{ super() }}{% endblock %}

{% block content %}
<div class="products-page">
    <h1>{{ page_content.title }}</h1>

    <div class="product-grid">
        {% for product in products %}
        <article class="product-card">
            <h2>{{ product.name }}</h2>
            <p class="price">${{ product.price }}</p>
            <a href="/products/{{ product.id }}">View Details</a>
        </article>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

### Template Helpers

Z8ter injects helpful functions:

```jinja
{# Generate URLs #}
{{ url_for('static', filename='images/logo.png') }}

{# Include Vite assets #}
{{ vite_script_tag("src/ts/app.ts") }}
```

## Request Access

Access request data in your views:

```python
class SearchPage(View):
    async def get(self, request: Request) -> Response:
        # Query parameters
        query = request.query_params.get("q", "")
        page = int(request.query_params.get("page", 1))

        # Headers
        user_agent = request.headers.get("user-agent")

        # Cookies
        session_id = request.cookies.get("session_id")

        # Client info
        client_host = request.client.host

        results = await search(query, page=page)

        return self.render(request, "pages/search.jinja", {
            "query": query,
            "results": results,
            "page": page
        })
```

## Form Handling

Handle form submissions with POST:

```python
from z8ter.responses import RedirectResponse


class ContactPage(View):
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/contact.jinja")

    async def post(self, request: Request) -> Response:
        form = await request.form()

        name = form.get("name")
        email = form.get("email")
        message = form.get("message")

        # Validate
        errors = {}
        if not name:
            errors["name"] = "Name is required"
        if not email:
            errors["email"] = "Email is required"

        if errors:
            return self.render(request, "pages/contact.jinja", {
                "errors": errors,
                "form_data": form
            })

        # Process the form
        await send_contact_email(name, email, message)

        # Redirect to success page
        return RedirectResponse(url="/contact/success", status_code=303)
```

## Protected Views

Use guards to protect views:

```python
from z8ter.auth.guards import login_required


class DashboardPage(View):
    @login_required
    async def get(self, request: Request) -> Response:
        user = request.state.user
        return self.render(request, "pages/dashboard.jinja", {
            "user": user
        })
```

See [Authentication](authentication.md) for more details.

## Redirects

Return redirect responses:

```python
from z8ter.responses import RedirectResponse


class OldPage(View):
    async def get(self, request: Request) -> Response:
        return RedirectResponse(url="/new-page")

class LoginPage(View):
    async def post(self, request: Request) -> Response:
        # After successful login...
        next_url = request.query_params.get("next", "/dashboard")
        return RedirectResponse(url=next_url, status_code=303)
```

## Error Handling

Handle errors gracefully:

```python
from starlette.exceptions import HTTPException


class ProductPage(View):
    async def get(self, request: Request) -> Response:
        product_id = request.path_params["id"]
        product = await get_product(product_id)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return self.render(request, "pages/product.jinja", {
            "product": product
        })
```

## Next Steps

- [API Endpoints](api-endpoints.md) - Build REST APIs
- [React Components](react-components.md) - Add interactive elements
- [Authentication](authentication.md) - Protect your pages
