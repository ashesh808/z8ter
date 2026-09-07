# Configuration

Z8ter exposes a callable configuration service backed by Starlette Config. Builder methods queue setup; services become available after `builder.build()`.

## Upgrading to 0.3.1

Z8ter 0.3.1 requires `starlette>=1.6,<2.0`; 0.3.0 used a pre-1.0 Starlette range. Upgrade Z8ter and resolve its dependencies together rather than retaining an old Starlette pin. Form-token CSRF requests now preserve the body for handlers and enforce an 8 MiB default buffer limit; configure `max_form_body_size` or use a header token for larger streaming uploads.

## Load and read configuration

```python
from z8ter.builders.app_builder import AppBuilder

builder = AppBuilder()
builder.use_config(".env")
builder.use_templating()
builder.use_vite()
app = builder.build(debug=False)
asgi_app = app.starlette_app

config = app.state.services["config"]
app_name = config("APP_NAME", default="My app")
port = config("PORT", cast=int, default=8000)
```

Inside a handler, use `request.app.state.services["config"]`. For ordinary keys, process environment variables override the selected `.env` file, followed by a supplied default. A missing key without a default raises `KeyError`; a missing `.env` file is allowed.

The special `BASE_DIR` key uses a process environment override or Z8ter's resolved app directory. Set the actual project root with `z8ter.set_app_dir(...)` or `Z8TER_APP_DIR`; changing the config value alone does not relocate project files.

### Types and validation

```python
from starlette.datastructures import CommaSeparatedStrings

feature_enabled = config("FEATURE_ENABLED", cast=bool, default=False)
allowed_hosts = config("ALLOWED_HOSTS", cast=CommaSeparatedStrings, default="localhost")
secret_key = config("APP_SESSION_KEY")
if len(secret_key) < 32:
    raise ValueError("APP_SESSION_KEY must contain at least 32 characters")
```

Boolean casting accepts the strings `true`, `1`, `false`, and `0`, ignoring case. Choose defaults and validate required application settings explicitly. Defining a setting such as `ALLOWED_HOSTS` does not install middleware that uses it.

## Framework settings

- `APP_SESSION_KEY`: signing key used by application sessions and, unless explicitly overridden, CSRF protection. App-session setup requires at least 32 characters.
- `LOGIN_PATH`: destination used by `login_required`; define it when using the guard.
- `APP_PATH`: destination used by `skip_if_authenticated`; define it when using the guard.
- `EMAIL_PROVIDER`: `console` by default, or `smtp`, when `use_email()` is enabled.
- `EMAIL_FROM`: default sender for the email service.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_USE_SSL`: settings read by the SMTP builder. Defaults are port 587, STARTTLS enabled, implicit SSL disabled.

```dotenv
APP_SESSION_KEY=replace-with-a-generated-private-key
LOGIN_PATH=/login
APP_PATH=/app/dashboard
EMAIL_PROVIDER=console
EMAIL_FROM=noreply@example.com
```

Session lifetime and cookie security are arguments to `SessionManager`, not automatic `SESSION_TTL` or `SESSION_COOKIE_SECURE` environment settings. See [Authentication](authentication.md).

### Settings read directly from the process environment

These are separate from the callable config service:

- `Z8TER_APP_DIR`: fallback project root when `set_app_dir()` has not been called.
- `Z8TER_DEBUG`: `AppBuilder.build()` uses `true` when no explicit `debug` argument is supplied. An explicit argument wins. The 0.3.1 CLI sets a default before importing `main.py`: false in prod, true in dev/LAN/WAN, while preserving an explicit environment value. Direct Uvicorn startup follows the debug choice in `main.py`.
- `Z8TER_MODE`: the core app's `dev`, `prod`, or `test` mode; this is separate from Uvicorn's reload flag.
- `Z8TER_APP_FACTORY`: optional override for the CLI ASGI factory import path. In 0.3.1 the default loader reuses `main.asgi_app`, then `main.app`, and falls back to `main.app_builder.build()` only if neither built callable is present.
- `DATABASE_URL`: read by `Database()` and database CLI commands when no explicit URL is supplied.
- `VITE_DEV_SERVER`: optional Vite asset server URL, read when `z8ter.vite` is imported.
- `VITE_ALWAYS_RELOAD_MANIFEST`: `true` disables manifest caching, also read at import.

`use_config(".env")` reads values through the service; it does not export them into `os.environ`. Export process settings before launching Python, or explicitly pass config values to the relevant constructor. `PORT` and `HOST` are not interpreted by `z8 run`; use Uvicorn arguments or `run_server(port=...)` instead.

## SQLite and other databases

The built-in `Database`, `SQLiteUserRepo`, and `SQLiteSessionRepo` support SQLite. PostgreSQL, Redis, and other stores require your own integrations/repositories; declaring a URL or pool setting does not install a driver.

Use an explicit absolute path to avoid ambiguous SQLite URL handling:

```python
from pathlib import Path
from z8ter.database import Database, init_database

path = Path("data/app.db").resolve()
database_url = f"sqlite:///{path.as_posix()}"
db = init_database(url=database_url)
```

The current parser treats `sqlite:///data/app.db` as `/data/app.db`. An absolute path assembled as above yields four slashes on Unix. `sqlite:///:memory:` is supported, but connections are thread-local: use a temporary file database for tests that cross threads.

## Frontend development and production

The generated starter uses Vite build-watch and a separate Tailwind CSS watcher. Its `npm run dev` starts those watchers and the Python server; it does not start a Vite HMR server. Leave `VITE_DEV_SERVER` unset for this workflow.

If you deliberately run a Vite dev server, export its URL before starting Python. Production uses `static/js/.vite/manifest.json`; build the assets with `npm run build` and leave `VITE_DEV_SERVER` unset. A missing manifest or entry produces an error; a configured dev server is not automatically replaced by the production manifest if unavailable.

## Environments and secrets

Choose the config filename explicitly, for example `builder.use_config(".env.production")`. Z8ter does not merge multiple environment files automatically.

Keep secrets out of version control:

```gitignore
.env
.env.*
!.env.example
```

Generate a private key with:

```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

Use distinct keys per environment. Enable [security middleware](security.md) and production cookie settings explicitly; a configuration file alone does not enable them.

## Next steps

- [CLI Reference](cli.md)
- [Authentication](authentication.md)
- [Interactive Islands](react-components.md)
