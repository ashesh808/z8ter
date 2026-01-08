# Z8ter Documentation

**Z8ter** is a lightweight, full-stack async Python web framework built on [Starlette](https://www.starlette.io/), designed for rapid development without compromising user experience.

## Features

- **SSR-First**: Server-side rendered pages with file-based routing
- **API Decorators**: Clean, decorator-based API endpoint definitions
- **React Islands**: Modern React components as Web Components for interactive UI
- **Vite Integration**: Fast development with HMR and optimized production builds
- **Pluggable Auth**: Protocol-based authentication with session management
- **Builder Pattern**: Composable application assembly with dependency validation
- **CLI Tools**: Scaffold pages, APIs, and entire projects

## Quick Example

```python
from z8ter.builders.app_builder import AppBuilder

# Build your application
builder = AppBuilder()
builder.use_config(".env")
builder.use_templating()
builder.use_vite()
builder.use_errors()

app = builder.build(debug=True)
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](getting-started.md) | Install Z8ter and create your first project |
| [Project Structure](project-structure.md) | Understand the Z8ter project layout |
| [Views & Pages](views.md) | Create server-rendered pages |
| [API Endpoints](api-endpoints.md) | Build REST API endpoints |
| [React Components](react-components.md) | Add interactive React islands |
| [Authentication](authentication.md) | Implement user authentication |
| [Configuration](configuration.md) | Configure your application |
| [CLI Reference](cli.md) | Command-line tools |

## Requirements

- Python 3.10+
- Node.js 18+ (for frontend tooling)

## Installation

```bash
pip install z8ter
```

## Philosophy

Z8ter embraces simplicity and convention over configuration:

1. **File-based routing**: Your file structure defines your URLs
2. **Separation of concerns**: Views, templates, content, and assets are organized logically
3. **Progressive enhancement**: Start with SSR, add interactivity where needed
4. **Developer experience**: Fast iteration with hot reload and helpful CLI tools

## License

MIT License - see [LICENSE](../LICENSE) for details.
