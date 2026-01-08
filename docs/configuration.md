# Configuration

Z8ter uses environment-based configuration with support for `.env` files, making it easy to manage settings across different environments.

## Environment Files

Create a `.env` file in your project root:

```env
# .env
DEBUG=true
SECRET_KEY=your-super-secret-key-change-in-production

# Database
DATABASE_URL=postgresql://user:pass@localhost/mydb

# Authentication
LOGIN_PATH=/login
APP_PATH=/app/dashboard
SESSION_TTL=2592000

# External Services
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=secret

# Vite (development)
VITE_DEV_SERVER=http://localhost:5173
```

## Loading Configuration

### Using the Builder

```python
from z8ter.builders.app_builder import AppBuilder

builder = AppBuilder()
builder.use_config(".env")  # Load from .env file
# ...
app = builder.build(debug=True)
```

### Accessing Configuration

Configuration is available as a service:

```python
# In views or API endpoints
async def get(self, request: Request) -> Response:
    config = request.app.state.services["config"]

    # Get a value (raises KeyError if missing)
    secret = config("SECRET_KEY")

    # Get with default
    debug = config("DEBUG", default=False)

    # Cast to type
    port = config("PORT", cast=int, default=8000)
    debug = config("DEBUG", cast=bool, default=False)
```

### Type Casting

The config function supports automatic type casting:

```python
# String (default)
name = config("APP_NAME")

# Integer
port = config("PORT", cast=int)

# Boolean (accepts: true, 1, yes, on)
debug = config("DEBUG", cast=bool)

# Float
rate = config("TAX_RATE", cast=float)

# List (comma-separated)
from starlette.config import CommaSeparatedStrings
hosts = config("ALLOWED_HOSTS", cast=CommaSeparatedStrings)

# Custom cast function
def parse_json(value):
    import json
    return json.loads(value)

data = config("JSON_CONFIG", cast=parse_json)
```

## Configuration Best Practices

### 1. Use Different Files per Environment

```
.env              # Default/development
.env.production   # Production overrides
.env.test         # Test overrides
```

Load the appropriate file:

```python
import os

env = os.getenv("APP_ENV", "development")
env_file = f".env.{env}" if env != "development" else ".env"

builder.use_config(env_file)
```

### 2. Never Commit Secrets

Add to `.gitignore`:

```gitignore
.env
.env.*
!.env.example
```

Create `.env.example` with placeholder values:

```env
# .env.example - Copy to .env and fill in values
DEBUG=true
SECRET_KEY=change-me
DATABASE_URL=postgresql://user:pass@localhost/mydb
```

### 3. Validate Required Settings

```python
# config/settings.py
from starlette.config import Config

config = Config(".env")

# Required settings (will raise if missing)
SECRET_KEY = config("SECRET_KEY")
DATABASE_URL = config("DATABASE_URL")

# Optional with defaults
DEBUG = config("DEBUG", cast=bool, default=False)
LOG_LEVEL = config("LOG_LEVEL", default="INFO")
```

### 4. Group Related Settings

```python
# config/database.py
from starlette.config import Config

config = Config(".env")

DATABASE_URL = config("DATABASE_URL")
DATABASE_POOL_SIZE = config("DATABASE_POOL_SIZE", cast=int, default=5)
DATABASE_MAX_OVERFLOW = config("DATABASE_MAX_OVERFLOW", cast=int, default=10)
```

```python
# config/auth.py
from starlette.config import Config

config = Config(".env")

SECRET_KEY = config("SECRET_KEY")
SESSION_TTL = config("SESSION_TTL", cast=int, default=86400 * 30)
LOGIN_PATH = config("LOGIN_PATH", default="/login")
APP_PATH = config("APP_PATH", default="/dashboard")
```

## Common Configuration Options

### Application Settings

```env
# Application mode
DEBUG=true
APP_ENV=development

# Server
HOST=127.0.0.1
PORT=8000

# Security
SECRET_KEY=your-secret-key-at-least-32-chars
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Authentication Settings

```env
# Session configuration
SESSION_TTL=2592000
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

# Redirect paths
LOGIN_PATH=/login
APP_PATH=/app/dashboard
LOGOUT_REDIRECT=/
```

### Database Settings

```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/mydb

# SQLite
DATABASE_URL=sqlite:///./data/app.db

# Connection pool
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
```

### Email Settings

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
EMAIL_FROM=noreply@example.com
```

### External APIs

```env
# Stripe
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET=my-bucket
```

### Frontend/Vite

```env
# Development server URL (enables HMR)
VITE_DEV_SERVER=http://localhost:5173

# Or leave empty for production mode
VITE_DEV_SERVER=
```

## App Directory Configuration

Z8ter resolves the application root directory with this precedence:

1. **Explicit**: `z8ter.set_app_dir("/path/to/app")`
2. **Environment**: `Z8TER_APP_DIR` environment variable
3. **Default**: Current working directory

```python
import z8ter

# Explicitly set app directory
z8ter.set_app_dir("/var/www/myapp")

# Get current app directory
print(z8ter.get_app_dir())

# Access resolved paths
print(z8ter.BASE_DIR)        # /var/www/myapp
print(z8ter.TEMPLATES_DIR)   # /var/www/myapp/templates
print(z8ter.STATIC_PATH)     # /var/www/myapp/static
```

## Runtime Configuration

### Accessing Config in Code

```python
# endpoints/views/settings.py
from z8ter.endpoints.view import View


class Settings(View):
    async def get(self, request: Request) -> Response:
        config = request.app.state.services["config"]

        return self.render(request, "pages/settings.jinja", {
            "app_name": config("APP_NAME", default="My App"),
            "debug_mode": config("DEBUG", cast=bool, default=False),
        })
```

### Using Config in Startup

```python
# main.py
from z8ter.builders.app_builder import AppBuilder

builder = AppBuilder()
builder.use_config(".env")

# Access config before build
# Note: Config is available after use_config()

app = builder.build(debug=True)

# After build, access via app.state
config = app.state.services["config"]
print(f"Running in {'debug' if config('DEBUG', cast=bool) else 'production'} mode")
```

## Environment-Specific Configuration

### Development

```env
# .env (development)
DEBUG=true
DATABASE_URL=sqlite:///./dev.db
VITE_DEV_SERVER=http://localhost:5173
LOG_LEVEL=DEBUG
```

### Production

```env
# .env.production
DEBUG=false
DATABASE_URL=postgresql://user:pass@prod-db:5432/app
VITE_DEV_SERVER=
LOG_LEVEL=WARNING
SESSION_COOKIE_SECURE=true
```

### Testing

```env
# .env.test
DEBUG=true
DATABASE_URL=sqlite:///:memory:
VITE_DEV_SERVER=
LOG_LEVEL=DEBUG
```

## Configuration Patterns

### Factory Pattern

```python
# config/factory.py
import os
from starlette.config import Config


def get_config():
    env = os.getenv("APP_ENV", "development")

    if env == "production":
        return Config(".env.production")
    elif env == "test":
        return Config(".env.test")
    else:
        return Config(".env")
```

### Settings Class

```python
# config/settings.py
from dataclasses import dataclass
from starlette.config import Config


@dataclass
class Settings:
    debug: bool
    secret_key: str
    database_url: str
    session_ttl: int
    login_path: str
    app_path: str

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "Settings":
        config = Config(env_file)
        return cls(
            debug=config("DEBUG", cast=bool, default=False),
            secret_key=config("SECRET_KEY"),
            database_url=config("DATABASE_URL"),
            session_ttl=config("SESSION_TTL", cast=int, default=2592000),
            login_path=config("LOGIN_PATH", default="/login"),
            app_path=config("APP_PATH", default="/dashboard"),
        )


# Usage
settings = Settings.from_env()
```

## Next Steps

- [CLI Reference](cli.md) - Command-line tools
- [Getting Started](getting-started.md) - Quick start guide
- [Authentication](authentication.md) - Auth configuration
