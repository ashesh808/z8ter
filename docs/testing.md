# Testing

Z8ter provides drop-in fakes and helpers (`z8ter.testing`) so application
tests never need a database or mail server.

## Test client

Z8ter apps are Starlette apps under the hood — use Starlette's
`TestClient` (requires `httpx`, included in the `dev` extra):

```python
from starlette.testclient import TestClient

client = TestClient(app.starlette_app)
response = client.get("/")
```

Use the client as a context manager when the app relies on lifespan
startup (e.g., background tasks):

```python
with TestClient(app.starlette_app) as client:
    ...
```

## In-memory repositories

`InMemorySessionRepo` and `InMemoryUserRepo` implement the full
`SessionRepo`/`UserRepo` contracts (hashing, expiry, revocation, rotation)
backed by plain dicts:

```python
import pytest
from z8ter.auth.crypto import hash_password
from z8ter.testing import InMemorySessionRepo, InMemoryUserRepo


@pytest.fixture()
def user_repo():
    repo = InMemoryUserRepo()
    repo.create_user(
        email="ada@example.com",
        password_hash=hash_password("correct horse"),
        name="Ada",
    )
    return repo
```

`InMemoryUserRepo` mirrors the `SQLiteUserRepo` surface
(`create_user`, `get_user_by_email`, `email_exists`, `update_password`,
…), so application code runs unchanged against either.

## Building a test app

`create_test_app()` assembles a minimal app with sane test defaults
(fixed secret key, error handlers, optional auth wiring):

```python
from starlette.testclient import TestClient
from z8ter.testing import InMemorySessionRepo, InMemoryUserRepo, create_test_app


def test_login_flow(user_repo):
    app = create_test_app(
        session_repo=InMemorySessionRepo(),
        user_repo=user_repo,
    )
    client = TestClient(app.starlette_app)
    ...
```

For full-stack tests against your real project (templates, pages, Vite),
point the path resolver at the project directory instead:

```python
import z8ter
z8ter.set_app_dir("path/to/project")
```

## Capturing email

Use `InMemoryEmailProvider` and assert on its `outbox`:

```python
from z8ter.testing import InMemoryEmailProvider

provider = InMemoryEmailProvider()
builder.use_email(provider=provider, default_from="noreply@test")
...
assert "Verify" in provider.outbox[0].subject
```
