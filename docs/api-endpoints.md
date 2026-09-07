# API Endpoints

Z8ter discovers subclasses of `API` under `endpoints/api`. Decorated methods become HTTP routes and must return a Starlette-compatible response, such as `JSONResponse`.

## Create an API

From your generated project directory:

```bash
uv run z8 create_api products
```

This creates `endpoints/api/products.py`. Replace the generated sample with your application's handlers. A complete small example is:

```python
# endpoints/api/products.py
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Products(API):
    @API.endpoint("GET", "/")
    async def list_products(self, request: Request) -> JSONResponse:
        return JSONResponse({"products": [{"id": 1, "name": "Notebook"}]})

    @API.endpoint("GET", "/{product_id:int}")
    async def get_product(self, request: Request) -> JSONResponse:
        product_id = request.path_params["product_id"]
        if product_id != 1:
            return JSONResponse({"error": "Product not found"}, status_code=404)
        return JSONResponse({"id": 1, "name": "Notebook"})
```

Requests reach `/api/products/` and `/api/products/1`. A route decorated with `"/"` includes a trailing slash; Starlette may redirect requests to its canonical URL.

## Route discovery

The default builder scans `endpoints.api` for `API` subclasses. A class in `endpoints.api.products` mounts at `/api/products`; a class in `endpoints.api.admin.reports` mounts at `/api/admin/reports`. Decorator paths extend that mount.

`@API.endpoint(method, path)` accepts one HTTP method and a path relative to the class mount. Starlette converters such as `/{id:int}`, `/{name}`, and `/{filepath:path}` are available through `request.path_params`.

Mount IDs are derived from the class's module. There is no supported public `api_id` override attribute, and the route builder does not add a second `/api` prefix. The lower-level `build_routes_from_apis(package_or_path)` and Starlette routing can be used for custom composition.

One instance of each API class is shared by its registered handlers. Do not put request-specific values on `self`; use local variables or `request.state`. Only decorated methods declared on the class are collected.

## Request bodies and validation

`request.json()` parses JSON; it does not validate an application schema. Check type and fields before use:

```python
# Add this method inside your API class.
@API.endpoint("POST", "/echo")
async def echo(self, request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except ValueError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(data, dict) or not isinstance(data.get("name"), str):
        return JSONResponse({"error": "name must be a string"}, status_code=422)
    return JSONResponse({"name": data["name"]})
```

Read query strings with `request.query_params`, headers with `request.headers`, and cookies with `request.cookies`. Validate numeric query parameters rather than assuming conversion will succeed.

### Forms and uploads

```python
# Add this method inside your API class.
@API.endpoint("POST", "/upload")
async def upload(self, request: Request) -> JSONResponse:
    async with request.form() as form:
        file = form.get("file")
        if not hasattr(file, "read"):
            return JSONResponse({"error": "A file is required"}, status_code=422)
        first_chunk = await file.read(1024)
        return JSONResponse({"filename": file.filename, "bytes_read": len(first_chunk)})
```

The context manager closes temporary upload files. This example reads only a small prefix; implement your application's storage, file checks, and request-size policy separately.

When CSRF is enabled, unsafe requests using a session cookie need a valid token. Form-token bodies are replayed to handlers with a default 8 MiB buffer limit; send `X-CSRF-Token` for uploads that should avoid CSRF buffering. API paths are not automatically exempt. See [Security](security.md).

## Responses and errors

Import response classes from `z8ter.responses`: `JSONResponse`, `Response`, `HTMLResponse`, `PlainTextResponse`, `RedirectResponse`, `FileResponse`, and `StreamingResponse`.

Returning a Python dict directly is not automatically converted to JSON. Response envelopes such as `{"ok": true, "data": ...}` are an application convention, not a framework requirement.

Use explicit `JSONResponse(..., status_code=...)` for a stable API error shape. You may also raise `starlette.exceptions.HTTPException`; `builder.use_errors()` installs Z8ter's error handlers, whose rendering depends on the request. Unexpected exceptions should not expose internal details in production.

## Authentication

Authentication requires [registered repositories and middleware](authentication.md). To return JSON instead of a login redirect:

```python
# Add this method inside your API class.
@API.endpoint("GET", "/me")
async def me(self, request: Request) -> JSONResponse:
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return JSONResponse({"id": user["id"], "name": user.get("name")})
```

Return an explicit set of public fields rather than serializing credentials. Authenticate webhook or bearer-token endpoints with their own checks before deciding whether a CSRF exemption is appropriate.

## Application services

Services you register are available through `request.app.state.services`; repositories are also exposed on application state by the auth builder. Z8ter does not create a general-purpose asynchronous `database.fetch_all()` service. Use the API of your configured storage integration and offload synchronous I/O as needed.

## Next steps

- [Views & Pages](views.md)
- [Authentication](authentication.md)
- [Interactive Islands](react-components.md)
