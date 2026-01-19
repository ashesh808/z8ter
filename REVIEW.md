# Z8ter Framework - Code Review

This document provides a detailed code review of the current Z8ter modules, identifying bugs, design issues, security concerns, and areas for improvement.

---

## Table of Contents

1. [z8ter/**init**.py - Core Package](#1-z8ter__init__py---core-package)
2. [z8ter/core.py - Application Wrapper](#2-z8tercorepy---application-wrapper)
3. [z8ter/auth/ - Authentication Module](#3-z8terauth---authentication-module)
4. [z8ter/builders/ - App Builder System](#4-z8terbuilders---app-builder-system)
5. [z8ter/cli/ - Command Line Tools](#5-z8tercli---command-line-tools)
6. [z8ter/endpoints/ - View & API System](#6-z8terendpoints---view--api-system)
7. [z8ter/vite.py - Frontend Asset Integration](#7-z8tervitepy---frontend-asset-integration)
8. [z8ter/config.py - Configuration](#8-z8terconfigpy---configuration)
9. [z8ter/errors.py - Error Handling](#9-z8tererrorspy---error-handling)
10. [z8ter-app/ - Reference Implementation](#10-z8ter-app---reference-implementation)

---

## 1. z8ter/**init**.py - Core Package

**File:** `z8ter/__init__.py`

### Issues Found

#### 1.1 Global Mutable State with Caching (Medium)

```python
_paths_cache: Paths | None = None
_templates_cache: Jinja2Templates | None = None
```

**Problem:** Global mutable state creates potential issues in multi-threaded or multi-process environments (common with Uvicorn workers).

**Impact:** Different workers may have inconsistent cache states. Race conditions possible during cache invalidation.

**Recommendation:** Consider using `contextvars` consistently or thread-local storage for all caches, not just `_APP_DIR`.

#### 1.2 ContextVar Not Fully Utilized (Low)

```python
_APP_DIR: contextvars.ContextVar[Path | None] = contextvars.ContextVar(...)
```

**Problem:** Only `_APP_DIR` uses `ContextVar`, but `_paths_cache` and `_templates_cache` are module-level globals. This inconsistency means the cache doesn't respect context boundaries.

**Recommendation:** Either make all caches context-aware or document that path changes affect all contexts.

#### 1.3 Lazy Attribute Access Performance (Low)

```python
def __getattr__(name: str) -> Any:
    paths = _current_paths()  # Called on every attribute access
    mapping: dict[str, Path] = {...}  # Dict created every time
```

**Problem:** Every access to `z8ter.BASE_DIR`, `z8ter.VIEWS_DIR`, etc. creates a new dictionary.

**Recommendation:** Cache the mapping or use a simpler conditional chain.

---

## 2. z8ter/core.py - Application Wrapper

**File:** `z8ter/core.py`

### Issues Found

#### 2.1 Emoji in Logging (Low)

```python
logger.warning("🧪 Z8ter running in DEBUG mode")
```

**Problem:** Emojis may not render correctly in all terminal environments or log aggregation systems.

**Recommendation:** Use plain text or make emoji usage configurable.

#### 2.2 Docstring Mismatch (Low)

```python
@property
def state(self):
    """Forward ASGI calls directly to the underlying Starlette app."""  # Wrong docstring
    return self.starlette_app.state
```

**Problem:** The docstring describes ASGI forwarding but the property returns state.

**Recommendation:** Fix docstring to: "Access the underlying Starlette app state."

#### 2.3 Mode Not Used After Validation (Low)

```python
self.mode: str = (mode or "prod").lower()
if self.mode not in ALLOWED_MODES:
    raise ValueError(...)
```

**Problem:** The `mode` attribute is stored but never used elsewhere in the codebase. It's validated but serves no purpose.

**Recommendation:** Either use mode to influence behavior or remove the validation complexity.

---

## 3. z8ter/auth/ - Authentication Module

**File:** `z8ter/auth/sessions.py`

### Issues Found

#### 3.1 Async Methods That Don't Await (High)

```python
async def start_session(self, user_id: str, ...) -> str:
    sid = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    self.session_repo.insert(...)  # NOT awaited!
    return sid

async def revoke_session(self, sid: str) -> bool:
    return self.session_repo.revoke(sid_plain=sid)  # NOT awaited!
```

**Problem:** Methods are declared `async` but call synchronous repository methods without `await`. If someone implements an async repository, these calls will return coroutines instead of results.

**Impact:** Silent failures with async repository implementations. The contract says "MUST be safe to call from async request handlers" but implementations will break.

**Recommendation:** Either:

- Make repository methods async and await them
- Remove `async` from SessionManager methods
- Document clearly that repos must be synchronous

#### 3.2 Cookie Security Default (Medium)

```python
async def set_session_cookie(self, resp, sid, *, secure: bool = True, ...):
```

But in `z8ter-app/endpoints/views/login.py`:

```python
await ms.set_session_cookie(resp, sid, secure=False)  # Hardcoded insecure!
```

**Problem:** While the default is secure, the reference implementation disables it without environment awareness.

**Recommendation:** Use `secure = not DEBUG` or read from config instead of hardcoding `False`.

---

**File:** `z8ter/auth/middleware.py`

### Issues Found

#### 3.3 Synchronous Repository Calls in Async Middleware (High)

```python
async def dispatch(self, request, call_next) -> Any:
    ...
    user_id = session_repo.get_user_id(sid)  # Sync call in async context
    if user_id:
        request.state.user = user_repo.get_user_by_id(user_id)  # Sync call
```

**Problem:** If repository implementations block (e.g., database queries), they will block the event loop.

**Recommendation:** Use `run_in_executor` for blocking calls or mandate async repository interfaces.

#### 3.4 No Error Handling for Repository Failures (Medium)

```python
user_id = session_repo.get_user_id(sid)
if user_id:
    request.state.user = user_repo.get_user_by_id(user_id)
```

**Problem:** If `get_user_id` or `get_user_by_id` raises an exception, the entire request fails. Database connectivity issues will crash requests.

**Recommendation:** Wrap in try/except and log errors, treating failures as unauthenticated.

---

**File:** `z8ter/auth/guards.py`

### Issues Found

#### 3.5 Open Redirect Vulnerability (High)

```python
def login_required(handler):
    @wraps(handler)
    async def wrapper(self, request: Request, *args, **kwargs):
        ...
        next_url = request.url.path
        if request.url.query:
            next_url = f"{next_url}?{request.url.query}"
        redirect_url = f"{login_path}?next={quote(next_url, safe='')}"
```

**Problem:** The docstring warns about open redirects but the code doesn't validate the `next` parameter when it's read back after login.

**Impact:** Attackers can craft URLs like `/login?next=https://evil.com` to redirect users after login.

**Recommendation:** Add validation that `next` is a relative path on the same domain.

#### 3.6 Hardcoded Service Key (Low)

```python
config = request.app.state.services["config"]
```

**Problem:** Direct dict access will raise `KeyError` if config service isn't registered.

**Recommendation:** Use `.get()` with a helpful error message, or validate at startup.

---

**File:** `z8ter/auth/crypto.py`

### Issues Found

#### 3.7 Silent Exception Swallowing (Medium)

```python
def verify_password(hash_: str, plain: str) -> bool:
    try:
        _PH.verify(hash_, plain)
        return True
    except Exception:  # Catches everything!
        return False
```

**Problem:** Catches all exceptions including `MemoryError`, `KeyboardInterrupt` (in Python < 3.11), etc. Also hides potentially important errors like malformed hash strings.

**Recommendation:** Catch specific `argon2.exceptions.VerifyMismatchError` and `argon2.exceptions.InvalidHashError`.

---

**File:** `z8ter/auth/contracts.py`

### Issues Found

#### 3.8 Protocol Methods Not Async (Medium)

```python
class SessionRepo(Protocol):
    def insert(self, ...) -> None: ...
    def revoke(self, ...) -> bool: ...
    def get_user_id(self, sid_plain: str) -> str | None: ...
```

**Problem:** Documentation says "All methods MUST be safe to call from async request handlers" but methods are synchronous. This creates confusion about whether to use `await`.

**Recommendation:** Either make protocol methods `async def` or clearly document that implementations must be non-blocking.

---

## 4. z8ter/builders/ - App Builder System

**File:** `z8ter/builders/app_builder.py`

### Issues Found

#### 4.1 Empty Lifespan Handler (Low)

```python
@asynccontextmanager
async def lifespan(app):
    try:
        yield
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        ...  # Empty
```

**Problem:** The lifespan handler catches exceptions but does nothing with them. The `finally` block is empty (just `...`).

**Recommendation:** Either remove the try/except or add proper cleanup/logging.

#### 4.2 Debug Mode Default (Medium)

```python
def build(self, debug: bool = True) -> Z8ter:
```

**Problem:** Debug mode defaults to `True`, which is unsafe for production if someone forgets to pass `debug=False`.

**Recommendation:** Default to `False` or read from environment variable.

#### 4.3 Context Mutation Side Effect (Medium)

```python
if step.kwargs:
    context.update(step.kwargs)  # Mutates shared context with step-specific data
step.func(context)
```

**Problem:** Step kwargs are merged into the shared context before execution. This can cause unintended data leakage between steps.

**Recommendation:** Pass kwargs as a separate argument to step functions.

---

**File:** `z8ter/builders/builder_functions.py`

### Issues Found

#### 4.4 Missing Space in Error Message (Low)

```python
raise RuntimeError(
    f"Z8ter: service '{name}' already registered.Pass replace=True to override."
)
```

**Problem:** Missing space before "Pass".

#### 4.5 Unsafe Config Injection (Medium)

```python
needs_config = hasattr(obj, "set_config") or hasattr(obj, "config")
if needs_config:
    ...
    if hasattr(obj, "config"):
        obj.config = cfg  # Direct attribute assignment
```

**Problem:** Directly setting `.config` attribute may overwrite existing data or fail on read-only properties.

**Recommendation:** Prefer `set_config()` method pattern exclusively.

#### 4.6 No Validation of Session Secret Strength (Medium)

```python
def use_app_sessions_builder(context: dict[str, Any]) -> None:
    secret_key = get_config_value(context=context, key="APP_SESSION_KEY")
    if not secret_key:
        raise TypeError("Z8ter: secret key is required for app sessions.")
```

**Problem:** Only checks if key exists, not if it's cryptographically strong.

**Recommendation:** Add minimum length check (e.g., 32 characters) and warn about weak keys.

---

## 5. z8ter/cli/ - Command Line Tools

**File:** `z8ter/cli/create.py`

### Issues Found

#### 5.1 Variable Shadows Builtin (Low)

```python
files = [
    ("create_page_templates/view.py.j2", view_path),
    ...
]
```

**Problem:** Variable `files` shadows the builtin `files` from `importlib.resources`.

**Recommendation:** Rename to `file_mappings` or `templates_to_create`.

#### 5.2 Overwrites Without Warning (Medium)

```python
for tpl_name, out_path in files:
    ...
    out_path.write_text(text, encoding="utf-8")  # Silently overwrites
```

**Problem:** If files exist, they're overwritten without confirmation or backup.

**Recommendation:** Check if file exists and prompt user or skip with warning.

#### 5.3 Simple Capitalize Fails for Multi-Word Names (Low)

```python
class_name = page_name.capitalize()  # "user_profile" -> "User_profile"
```

**Problem:** `capitalize()` only capitalizes the first letter. Names like "user_profile" become "User_profile" not "UserProfile".

**Recommendation:** Use proper PascalCase conversion: `"".join(word.capitalize() for word in page_name.split("_"))`.

---

**File:** `z8ter/cli/run_server.py`

### Issues Found

#### 5.4 Hardcoded App Factory Path (Medium)

```python
uvicorn.run(
    "main:app_builder.build",
    factory=True,
    ...
)
```

**Problem:** Assumes the app is always at `main:app_builder.build`. Non-standard project structures will fail.

**Recommendation:** Make this configurable via argument or environment variable.

#### 5.5 Prod Mode Binds to Localhost (Potential Issue)

```python
elif mode == "prod":
    host = "127.0.0.1"  # Not 0.0.0.0
```

**Problem:** Production mode binds to localhost only, which won't work in containerized environments where you need to bind to 0.0.0.0.

**Recommendation:** Document this clearly or change default. Containers need `0.0.0.0`.

---

## 6. z8ter/endpoints/ - View & API System

**File:** `z8ter/endpoints/view.py`

### Issues Found

#### 6.1 Unusual **init** Pattern (Low)

```python
def __init__(
    self,
    scope: Scope | None = None,
    receive: Receive | None = None,
    send: Send | None = None,
) -> None:
    if scope is not None and receive is not None and send is not None:
        super().__init__(scope, receive, send)
```

**Problem:** This allows creating View instances without proper ASGI setup, which could lead to confusing errors when methods expect scope/receive/send to exist.

**Recommendation:** Document why this pattern exists (testing) more prominently.

---

**File:** `z8ter/endpoints/api.py`

### Issues Found

#### 6.2 Legacy Quirk Without Migration Path (Medium)

```python
prefix: str = f"{cls._api_id}".removeprefix("endpoints")
```

**Problem:** Comment says "A historical quirk trims a leading 'endpoints' segment" but doesn't explain why or how to migrate away from it.

**Recommendation:** Either remove the quirk or add deprecation warning.

#### 6.3 Single Instance for All Routes (Medium)

```python
inst: API = cls()  # One instance
routes: list[Route] = [
    Route(subpath, endpoint=getattr(inst, func_name), methods=[method])
    for (method, subpath, func_name) in getattr(cls, "_endpoints", [])
]
```

**Problem:** All routes share a single instance. If an endpoint method stores state on `self`, it will leak between requests.

**Recommendation:** Either create new instances per request or document this limitation clearly.

#### 6.4 Type Ignore Comment (Low)

```python
fn._z8_endpoint = method.upper(), path  # type: ignore[attr-defined]
```

**Problem:** Adding arbitrary attributes to functions is a common pattern but fragile. Type checkers are suppressed.

**Recommendation:** Consider using a registry dict instead of function attributes.

---

**File:** `z8ter/endpoints/helpers.py`

### Issues Found

#### 6.5 Silent Content Loading Failure (Medium)

```python
if data is None:
    data = {}
    logger.warning(f"No content found for '{page_id}' under {root})")  # Extra )
```

**Problem:**

1. Extra `)` in log message
2. Missing content files only generate a warning, which may be missed

**Recommendation:** Fix typo. Consider making missing content an error in development mode.

#### 6.6 Last Match Wins Silently (Low)

```python
candidates = [
    root / f"{rel}.json",
    root / f"{rel}.yaml",
    root / f"{rel}.yml",
]
for path in candidates:
    if path.is_file():
        ...  # Overwrites data each time
```

**Problem:** If multiple content files exist (e.g., `about.json` AND `about.yaml`), the last one wins silently.

**Recommendation:** Warn if multiple files found, or break after first match.

---

## 7. z8ter/vite.py - Frontend Asset Integration

### Issues Found

#### 7.1 No Dev Server Fallback (Medium)

```python
if VITE_DEV_SERVER:
    return Markup(
        f'<script type="module" src="{VITE_DEV_SERVER}/{entry}"></script>'
    )
```

**Problem:** If `VITE_DEV_SERVER` is set but the dev server isn't running, pages will fail to load scripts with no helpful error.

**Recommendation:** Add a health check or timeout with fallback to built assets.

#### 7.2 No Cache Invalidation on Manifest Change in Prod (Low)

```python
if _manifest_cache is None or _manifest_mtime != stat.st_mtime:
    _manifest_cache = json.loads(path.read_text())
```

**Problem:** Caching based on mtime works but can fail if deployment replaces files without changing mtime (some container deployments).

**Recommendation:** Consider using file hash or reload on every request in debug mode.

---

## 8. z8ter/config.py - Configuration

### Issues Found

#### 8.1 Direct Mutation of Config Internal State (Medium)

```python
cf: Config = Config(env_file)
cf.file_values["BASE_DIR"] = str(z8ter.BASE_DIR)  # Mutates internal dict
```

**Problem:** Directly accessing `file_values` is relying on Starlette's internal implementation details.

**Recommendation:** Use environment variables or a wrapper class instead.

---

## 9. z8ter/errors.py - Error Handling

### Issues Found

#### 9.1 JSON-Only Error Responses (Medium)

```python
async def http_exc(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "error": {"message": exc.detail}},
        ...
    )
```

**Problem:** All errors return JSON, even for browser requests that expect HTML. A 404 for a web page returns JSON.

**Recommendation:** Check `Accept` header and return HTML for browser requests.

#### 9.2 No Logging of Internal Errors (Medium)

```python
async def any_exc(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "error": {"message": "Internal server error"}},
        status_code=500,
    )
```

**Problem:** Internal errors are swallowed without logging. Debugging production issues becomes difficult.

**Recommendation:** Log the full exception with traceback before returning generic message.

---

## 10. z8ter-app/ - Reference Implementation

**File:** `z8ter-app/main.py`

### Issues Found

#### 10.1 No Error Handling for Missing .env (Low)

```python
app_builder.use_config(".env")
```

**Problem:** If `.env` file is missing, behavior is unclear.

**Recommendation:** Document that `.env` is optional or add explicit check.

---

**File:** `z8ter-app/app/identity/adapter/session_repo.py`

### Issues Found

#### 10.2 Plaintext Session Storage (High - Security)

```python
def insert(self, *, sid_plain: str, ...):
    self._sessions[sid_plain] = {...}  # Stores plaintext SID as key!
```

**Problem:** The contract explicitly states "IMPLEMENTORS MUST hash before persisting" but the reference implementation stores plaintext session IDs.

**Impact:** If the session store is compromised, all session IDs are exposed and can be used for session hijacking.

**Recommendation:** Hash session IDs before using as dict keys, even in the in-memory implementation, to set the right example.

#### 10.3 No Session Cleanup (Low)

```python
def get_user_id(self, sid_plain: str) -> Optional[str]:
    session = self._sessions.get(sid_plain)
    ...
    if session["expires_at"] <= datetime.now(timezone.utc):
        return None  # Expired but still stored
```

**Problem:** Expired sessions are never removed from memory, causing unbounded memory growth.

**Recommendation:** Add periodic cleanup or remove expired sessions on access.

---

**File:** `z8ter-app/endpoints/views/login.py`

### Issues Found

#### 10.4 Insecure Cookie in Production (High)

```python
await ms.set_session_cookie(resp, sid, secure=False)
```

**Problem:** `secure=False` sends cookies over HTTP, allowing session hijacking via network sniffing.

**Recommendation:** Read from config: `secure = config("COOKIE_SECURE", cast=bool, default=True)`

#### 10.5 Timing Attack on User Lookup (Low)

```python
user = await mu.get_user_email(email)
if user is None:
    return RedirectResponse("/login?e=badcreds", status_code=303)
ok = verify_password(user["pwd_hash"], pwd)
if not ok:
    return RedirectResponse("/login?e=badcreds", status_code=303)
```

**Problem:** Returns immediately if user not found but performs password verification if found. Timing difference reveals whether email exists.

**Recommendation:** Always perform a dummy password check even when user not found.

---

**File:** `z8ter-app/endpoints/views/register.py`

### Issues Found

#### 10.6 No Duplicate Email Check (High)

```python
async def post(self, request: Request) -> Response:
    ...
    await mu.create_user(email, pwd)  # No check if email exists
    return RedirectResponse("/login?m=signup_ok", status_code=303)
```

**Problem:** If a user tries to register with an existing email, behavior is undefined (likely overwrites or errors).

**Recommendation:** Check if email exists first and return appropriate error.

#### 10.7 Weak Password Validation (Medium)

```python
if (not email) or (not pwd) or (pwd != pwd2):
    return RedirectResponse("/register?e=invalid", status_code=303)
```

**Problem:** Only checks that password is non-empty and matches confirmation. No minimum length, complexity, or common password checks.

**Recommendation:** Add minimum password length (8+ characters) and optionally check against common passwords.

---

## Summary of Critical Issues

| Severity   | Count | Examples                                                                        |
| ---------- | ----- | ------------------------------------------------------------------------------- |
| **High**   | 6     | Async/sync mismatch, open redirect, plaintext session storage, insecure cookies |
| **Medium** | 15    | No error logging, JSON-only errors, no duplicate email check, timing attacks    |
| **Low**    | 12    | Typos, naming issues, documentation mismatches                                  |

### Priority Fixes

1. **Fix async/sync contract** - SessionManager methods and repository interface need consistent async handling
2. **Validate redirect URLs** - Add open redirect protection to guards
3. **Hash session IDs** - Even in-memory implementation should hash to set correct example
4. **Make cookie security configurable** - Don't hardcode `secure=False`
5. **Log internal errors** - Add logging to error handlers
6. **Content-negotiate error responses** - Return HTML for browser requests

---

## Architectural Recommendations

1. **Define async interface clearly** - Either all async or all sync, not mixed
2. **Add type stubs** - Create `.pyi` files for better IDE support
3. **Integration tests** - Add tests that verify the full request cycle
4. **Security audit** - Consider a formal security review before v1.0
5. **Configuration schema** - Add validation for required config values at startup
