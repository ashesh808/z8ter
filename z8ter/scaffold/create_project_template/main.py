import os

from z8ter.builders.app_builder import AppBuilder

# Determine if we're in debug mode (default: True for development)
DEBUG = os.getenv("Z8TER_DEBUG", "true").lower() == "true"

app_builder = AppBuilder()
app_builder.use_config(".env")
app_builder.use_templating()
app_builder.use_vite()
app_builder.use_errors()
app_builder.use_security_headers()
app_builder.use_health_check()

# Build the application
app = app_builder.build(debug=DEBUG)

# For uvicorn: `uvicorn main:asgi_app`
asgi_app = app.starlette_app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:asgi_app", host="0.0.0.0", port=8000, reload=DEBUG)
