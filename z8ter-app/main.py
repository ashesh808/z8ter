import os

from app.identity.adapter.session_repo import InMemorySessionRepo
from app.identity.adapter.user_repo import InMemoryUserRepo
from z8ter.builders.app_builder import AppBuilder
from z8ter.security.rate_limit import RateLimitConfig

# Get secret key from environment (required for session security)
SECRET_KEY = os.getenv("APP_SESSION_KEY", "")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    # Generate a development key if not set (NOT FOR PRODUCTION)
    import secrets

    SECRET_KEY = secrets.token_hex(32)
    print("[WARNING] Using generated secret key. Set APP_SESSION_KEY in production.")

app_builder = AppBuilder()
app_builder.use_config(".env")
app_builder.use_templating()
app_builder.use_vite()

# Security middleware (order matters - added first, executed last)
app_builder.use_security_headers(
    enable_hsts=os.getenv("ENABLE_HSTS", "false").lower() == "true",
)
app_builder.use_rate_limiting(
    requests_per_minute=60,
    rules=[
        # Stricter limits for auth endpoints
        RateLimitConfig(requests=10, window_seconds=60, paths=["/login", "/register"]),
    ],
)
app_builder.use_csrf(
    exempt_paths=["/api/"],  # APIs use token auth, not cookies
    cookie_secure=os.getenv("SECURE_COOKIES", "true").lower() == "true",
)

# Auth with secure session storage
app_builder.use_auth_repos(
    session_repo=InMemorySessionRepo(secret_key=SECRET_KEY),
    user_repo=InMemoryUserRepo(),
)
app_builder.use_authentication()
app_builder.use_errors()
app_builder.use_app_sessions()

if __name__ == "__main__":
    # Debug mode now defaults to False unless Z8TER_DEBUG=true
    app = app_builder.build()
