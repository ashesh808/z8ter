# Z8ter Documentation

**Z8ter** is an async Python web framework built on [Starlette](https://www.starlette.io/). Render pages with Jinja, organize views and APIs by file, and add interactive components where you need them.

The Z8ter 0.3.1 starter pairs Python with **Solid, TypeScript, Vite, Tailwind CSS, and DaisyUI**. The documentation website itself uses Next.js and React.

## Features

- **SSR-first pages:** Jinja templates and file-based route discovery
- **API decorators:** Define JSON endpoints on Python classes
- **Interactive islands:** The starter registers Solid components as custom elements
- **Vite integration:** Build JavaScript bundles and a manifest for server-rendered templates
- **Pluggable authentication:** Configure repositories, sessions, signed tokens, and account lockout
- **Optional security tools:** Enable CSRF protection, rate limiting, and other middleware explicitly
- **Transactional email:** Choose a provider for asynchronous email delivery
- **Background tasks:** Run in-process asynchronous tasks and recurring work
- **Testing utilities:** Use in-memory repositories and an email outbox in app tests
- **Application builder:** Register the integrations your application needs
- **CLI tools:** Scaffold projects, pages, and APIs

## Start a Project

With Python 3.10+, Node.js 22.12+, npm, and uv installed:

```bash
uvx --from z8ter z8 new myapp
cd myapp
uv sync
npm install
npm run build
uv run npm run dev
```

Once the server and asset watchers are ready, open [http://127.0.0.1:8000](http://127.0.0.1:8000). The development command watches Python, CSS, and TypeScript; refresh the browser after frontend changes.

No database is required for the starter. For the pip alternative and a guided explanation of each command, see [Getting Started](getting-started.md).

## Application Configuration

The generated application registers its integrations with `AppBuilder`:

```python
import os

from z8ter.builders.app_builder import AppBuilder

app_builder = AppBuilder()
app_builder.use_config(".env")
app_builder.use_templating()
app_builder.use_vite()
app_builder.use_errors()
app_builder.use_security_headers()
app_builder.use_health_check()

app = app_builder.build(
    debug=os.getenv("Z8TER_DEBUG", "true").lower() == "true"
)
```

Set `Z8TER_DEBUG=false` in your production environment. Add sessions, authentication, CSRF protection, or rate limiting through the relevant builder methods when your app needs them.

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](getting-started.md) | Create an app with uv or pip, build assets, and run it |
| [Project Structure](project-structure.md) | Understand the Z8ter project layout |
| [Views & Pages](views.md) | Create server-rendered pages |
| [API Endpoints](api-endpoints.md) | Build JSON API endpoints |
| [Interactive Islands](react-components.md) | Add Solid custom elements and page-specific browser behavior |
| [Authentication](authentication.md) | Configure user authentication |
| [Security](security.md) | Configure middleware, lockout, tokens, and secrets |
| [Email](email.md) | Send transactional email |
| [Background Tasks](background-tasks.md) | Run recurring and one-off work |
| [Testing](testing.md) | Test apps with in-memory fakes |
| [Configuration](configuration.md) | Configure your application |
| [CLI Reference](cli.md) | Use the command-line tools |

## Philosophy

1. **Conventions for routes:** Views and APIs live in predictable locations.
2. **Clear responsibilities:** Keep handlers, templates, content, and assets organized.
3. **Progressive enhancement:** Start with rendered HTML and add browser-side behavior.
4. **Tools you can compose:** Choose the integrations that fit your application.

## License

MIT License.
