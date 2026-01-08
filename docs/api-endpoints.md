# API Endpoints

Z8ter provides a clean, decorator-based approach to building REST APIs. API classes group related endpoints and are automatically discovered and mounted.

## Creating an API

### Using the CLI

```bash
z8 create_api products
```

This generates `endpoints/api/products.py`:

```python
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Products(API):
    @API.endpoint("GET", "/")
    async def list_products(self, request: Request):
        return JSONResponse({"ok": True, "products": []})
```

### Manual Creation

Create `endpoints/api/products.py`:

```python
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Products(API):
    @API.endpoint("GET", "/")
    async def list_all(self, request: Request):
        products = await fetch_products()
        return JSONResponse({
            "ok": True,
            "data": products
        })

    @API.endpoint("GET", "/{product_id:int}")
    async def get_one(self, request: Request):
        product_id = request.path_params["product_id"]
        product = await fetch_product(product_id)

        if not product:
            return JSONResponse({
                "ok": False,
                "error": {"message": "Product not found"}
            }, status_code=404)

        return JSONResponse({
            "ok": True,
            "data": product
        })

    @API.endpoint("POST", "/")
    async def create(self, request: Request):
        data = await request.json()
        product = await create_product(data)
        return JSONResponse({
            "ok": True,
            "data": product
        }, status_code=201)

    @API.endpoint("PUT", "/{product_id:int}")
    async def update(self, request: Request):
        product_id = request.path_params["product_id"]
        data = await request.json()
        product = await update_product(product_id, data)
        return JSONResponse({
            "ok": True,
            "data": product
        })

    @API.endpoint("DELETE", "/{product_id:int}")
    async def delete(self, request: Request):
        product_id = request.path_params["product_id"]
        await delete_product(product_id)
        return JSONResponse({
            "ok": True,
            "message": "Product deleted"
        })
```

## The API Class

### Structure

```python
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class MyAPI(API):
    # Optional: override the default mount path
    # Default is derived from module: api.users → /users
    api_id = "custom-path"

    @API.endpoint("GET", "/")
    async def my_endpoint(self, request: Request):
        return JSONResponse({"message": "Hello"})
```

### The `@API.endpoint` Decorator

```python
@API.endpoint(method: str, path: str)
```

- **method**: HTTP method (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, etc.)
- **path**: Route path relative to the API mount point

```python
class Users(API):
    # GET /api/users/
    @API.endpoint("GET", "/")
    async def list_users(self, request: Request):
        pass

    # GET /api/users/123
    @API.endpoint("GET", "/{user_id:int}")
    async def get_user(self, request: Request):
        pass

    # POST /api/users/
    @API.endpoint("POST", "/")
    async def create_user(self, request: Request):
        pass

    # PUT /api/users/123/profile
    @API.endpoint("PUT", "/{user_id:int}/profile")
    async def update_profile(self, request: Request):
        pass
```

## URL Routing

### Automatic Mount Points

The API is mounted based on its file location:

| File | Mount Point |
|------|-------------|
| `endpoints/api/users.py` | `/api/users` |
| `endpoints/api/products.py` | `/api/products` |
| `endpoints/api/auth.py` | `/api/auth` |

### Path Parameters

Use Starlette path parameter syntax:

```python
class Orders(API):
    # /api/orders/123
    @API.endpoint("GET", "/{order_id:int}")
    async def get_order(self, request: Request):
        order_id = request.path_params["order_id"]
        return JSONResponse({"order_id": order_id})

    # /api/orders/123/items/456
    @API.endpoint("GET", "/{order_id:int}/items/{item_id:int}")
    async def get_order_item(self, request: Request):
        order_id = request.path_params["order_id"]
        item_id = request.path_params["item_id"]
        return JSONResponse({
            "order_id": order_id,
            "item_id": item_id
        })
```

Parameter types:
- `{param}` - String (default)
- `{param:int}` - Integer
- `{param:float}` - Float
- `{param:path}` - Path (matches slashes)

## Request Handling

### JSON Body

```python
@API.endpoint("POST", "/")
async def create(self, request: Request):
    data = await request.json()
    name = data.get("name")
    email = data.get("email")
    # ...
```

### Query Parameters

```python
@API.endpoint("GET", "/search")
async def search(self, request: Request):
    query = request.query_params.get("q", "")
    page = int(request.query_params.get("page", 1))
    limit = int(request.query_params.get("limit", 20))

    results = await search_products(query, page, limit)
    return JSONResponse({
        "ok": True,
        "data": results,
        "page": page,
        "limit": limit
    })
```

### Headers

```python
@API.endpoint("GET", "/protected")
async def protected(self, request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return JSONResponse({
            "ok": False,
            "error": {"message": "Missing authorization header"}
        }, status_code=401)
    # Validate token...
```

### Form Data

```python
@API.endpoint("POST", "/upload")
async def upload(self, request: Request):
    form = await request.form()
    file = form.get("file")

    if file:
        contents = await file.read()
        # Process file...

    return JSONResponse({"ok": True})
```

## Response Types

### JSONResponse

The most common response type for APIs:

```python
from z8ter.responses import JSONResponse

# Success response
return JSONResponse({
    "ok": True,
    "data": {"id": 1, "name": "Product"}
})

# With status code
return JSONResponse({
    "ok": True,
    "data": product
}, status_code=201)

# Error response
return JSONResponse({
    "ok": False,
    "error": {"message": "Not found", "code": "NOT_FOUND"}
}, status_code=404)
```

### Other Response Types

```python
from z8ter.responses import (
    Response,
    PlainTextResponse,
    HTMLResponse,
    RedirectResponse,
    FileResponse,
    StreamingResponse
)

# Plain text
return PlainTextResponse("Hello, World!")

# HTML
return HTMLResponse("<h1>Hello</h1>")

# Redirect
return RedirectResponse(url="/new-location")

# File download
return FileResponse(
    path="/path/to/file.pdf",
    filename="document.pdf"
)

# Streaming
async def generate():
    for i in range(10):
        yield f"data: {i}\n\n"
        await asyncio.sleep(1)

return StreamingResponse(generate(), media_type="text/event-stream")
```

## Response Conventions

We recommend consistent response shapes:

### Success Response

```json
{
    "ok": true,
    "data": { ... }
}
```

### Error Response

```json
{
    "ok": false,
    "error": {
        "message": "Human-readable message",
        "code": "ERROR_CODE"
    }
}
```

### List Response

```json
{
    "ok": true,
    "data": [ ... ],
    "meta": {
        "total": 100,
        "page": 1,
        "limit": 20
    }
}
```

## Error Handling

### HTTP Exceptions

```python
from starlette.exceptions import HTTPException

@API.endpoint("GET", "/{id:int}")
async def get_item(self, request: Request):
    item_id = request.path_params["id"]
    item = await fetch_item(item_id)

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    return JSONResponse({"ok": True, "data": item})
```

### Custom Error Responses

```python
@API.endpoint("POST", "/")
async def create(self, request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({
            "ok": False,
            "error": {"message": "Invalid JSON body"}
        }, status_code=400)

    # Validation
    errors = validate_data(data)
    if errors:
        return JSONResponse({
            "ok": False,
            "error": {
                "message": "Validation failed",
                "details": errors
            }
        }, status_code=422)

    # Create resource...
```

## Authentication

### Accessing the Current User

```python
@API.endpoint("GET", "/me")
async def get_current_user(self, request: Request):
    user = getattr(request.state, "user", None)

    if not user:
        return JSONResponse({
            "ok": False,
            "error": {"message": "Not authenticated"}
        }, status_code=401)

    return JSONResponse({
        "ok": True,
        "data": user
    })
```

### Protected Endpoints

```python
from functools import wraps

def require_auth(func):
    @wraps(func)
    async def wrapper(self, request: Request):
        user = getattr(request.state, "user", None)
        if not user:
            return JSONResponse({
                "ok": False,
                "error": {"message": "Authentication required"}
            }, status_code=401)
        return await func(self, request)
    return wrapper


class SecureAPI(API):
    @API.endpoint("GET", "/secret")
    @require_auth
    async def secret_data(self, request: Request):
        return JSONResponse({
            "ok": True,
            "data": {"secret": "value"}
        })
```

## Accessing Services

Access application services via `request.app.state.services`:

```python
@API.endpoint("GET", "/")
async def list_items(self, request: Request):
    # Access registered services
    services = request.app.state.services
    config = services.get("config")
    db = services.get("database")

    items = await db.fetch_all("SELECT * FROM items")
    return JSONResponse({"ok": True, "data": items})
```

## Complete Example

```python
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Tasks(API):
    """Task management API"""

    @API.endpoint("GET", "/")
    async def list_tasks(self, request: Request):
        """List all tasks with optional filtering"""
        status = request.query_params.get("status")
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))

        tasks = await self._get_tasks(status, page, limit)
        total = await self._count_tasks(status)

        return JSONResponse({
            "ok": True,
            "data": tasks,
            "meta": {
                "total": total,
                "page": page,
                "limit": limit
            }
        })

    @API.endpoint("POST", "/")
    async def create_task(self, request: Request):
        """Create a new task"""
        data = await request.json()

        # Validate
        if not data.get("title"):
            return JSONResponse({
                "ok": False,
                "error": {"message": "Title is required"}
            }, status_code=400)

        task = await self._create_task(data)

        return JSONResponse({
            "ok": True,
            "data": task
        }, status_code=201)

    @API.endpoint("GET", "/{task_id:int}")
    async def get_task(self, request: Request):
        """Get a specific task"""
        task_id = request.path_params["task_id"]
        task = await self._get_task(task_id)

        if not task:
            return JSONResponse({
                "ok": False,
                "error": {"message": "Task not found"}
            }, status_code=404)

        return JSONResponse({
            "ok": True,
            "data": task
        })

    @API.endpoint("PATCH", "/{task_id:int}")
    async def update_task(self, request: Request):
        """Update a task"""
        task_id = request.path_params["task_id"]
        data = await request.json()

        task = await self._update_task(task_id, data)
        if not task:
            return JSONResponse({
                "ok": False,
                "error": {"message": "Task not found"}
            }, status_code=404)

        return JSONResponse({
            "ok": True,
            "data": task
        })

    @API.endpoint("DELETE", "/{task_id:int}")
    async def delete_task(self, request: Request):
        """Delete a task"""
        task_id = request.path_params["task_id"]
        deleted = await self._delete_task(task_id)

        if not deleted:
            return JSONResponse({
                "ok": False,
                "error": {"message": "Task not found"}
            }, status_code=404)

        return JSONResponse({
            "ok": True,
            "message": "Task deleted"
        })

    # Helper methods
    async def _get_tasks(self, status, page, limit):
        # Database query...
        pass

    async def _count_tasks(self, status):
        # Count query...
        pass

    async def _get_task(self, task_id):
        # Fetch single task...
        pass

    async def _create_task(self, data):
        # Insert task...
        pass

    async def _update_task(self, task_id, data):
        # Update task...
        pass

    async def _delete_task(self, task_id):
        # Delete task...
        pass
```

## Next Steps

- [React Components](react-components.md) - Build interactive frontends
- [Authentication](authentication.md) - Secure your APIs
- [Configuration](configuration.md) - Configure your application
