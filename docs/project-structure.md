# Project Structure

The packaged `z8 new` starter uses the following directories. Authentication routes, domain services, and extra APIs are application additions, not automatically generated features.

```text
myapp/
  main.py                         # app_builder, app, and asgi_app
  pyproject.toml                  # uv/Python project
  requirements.txt                # pip-compatible dependencies
  package.json
  package-lock.json
  vite.config.ts
  tsconfig.json
  endpoints/
    views/
      index.py                    # /
      about.py                    # /about
    api/
      hello.py                    # /api/hello/
  templates/
    base.jinja
    pages/
      index.jinja
      about.jinja
    server-components/            # Jinja macros
  content/
    index.yaml
    about.yaml
  src/
    css/app.css                   # Tailwind entry
    ts/
      app.ts                      # Page module loader
      pages/
        index.ts
        about.ts
      ui-components/              # Solid custom elements
      utils/
  static/
    css/output.css                # Tailwind output
    js/.vite/manifest.json        # Vite manifest
    js/assets/                    # Built JS assets
  Dockerfile
  docker-compose.yml
```

## Views and routes

The default builder scans `endpoints.views` for `View` subclasses. A Python file without a `View` class does not become a page route.

```text
endpoints/views/index.py             → /
endpoints/views/about.py             → /about
endpoints/views/products/index.py    → /products
endpoints/views/products/detail.py   → /products/detail
```

A view's `path` class attribute can override its URL, including Starlette path parameters. Its template filename is selected explicitly in `self.render()`; it is not inferred from the URL.

## API classes

The default builder scans `endpoints.api` for `API` subclasses. Module paths determine mount paths, and `@API.endpoint` defines paths inside each mount:

```text
endpoints/api/hello.py               → /api/hello
endpoints/api/admin/reports.py       → /api/admin/reports
```

A decorator path of `"/"` gives an endpoint with a trailing slash. See [API Endpoints](api-endpoints.md) for the shared-instance contract and custom routing.

## Templates and page content

`templates/base.jinja` provides the outer HTML. Page templates normally extend it, and `server-components` contains reusable Jinja macros.

`View.render()` derives a `page_id` from the view module. For `endpoints.views.app.dashboard`, the ID is `app.dashboard`; content is looked up as `content/app/dashboard.json`, `.yaml`, then `.yml`. The first existing format wins. Missing content gives an empty `page_content` mapping; malformed content raises an error.

The generated layout puts `data-page="{{ page_id }}"` on **body**. The TypeScript entry reads that attribute, converts dots to directories, and imports the matching file under `src/ts/pages`.

## Frontend files

The generated starter uses Solid and `solid-element`, with `vite-plugin-solid`. It does not use React by default. Import custom elements from the page module that needs them; an optional `pages/common.ts` can hold imports needed across pages.

Vite builds JavaScript into `static/js`; Tailwind separately builds `static/css/output.css`. The `/static` mount is added only when that directory exists. See [Interactive Islands](react-components.md).

## Application logic

You may add an `app/` directory for domain logic, repositories, or services. Its shape is your application's choice; Z8ter does not discover or register all service objects automatically.

## Path resolution

```python
from pathlib import Path
import z8ter

z8ter.set_app_dir(Path("/absolute/path/to/myapp"))
print(z8ter.BASE_DIR)
print(z8ter.VIEWS_DIR)
print(z8ter.TEMPLATES_DIR)
print(z8ter.STATIC_PATH)
print(z8ter.API_DIR)
print(z8ter.TS_DIR)
```

The app root uses an explicit `set_app_dir()` value first, then `Z8TER_APP_DIR`, then the working directory. The CLI sets it to the current working directory.

Low-level `build_routes_from_pages(package_or_path)` and `build_routes_from_apis(package_or_path)` accept custom scan roots. To use them, compose the resulting routes yourself; calling them does not change the default `AppBuilder` scan directories. Ensure custom modules can be imported.

## Next steps

- [Views & Pages](views.md)
- [API Endpoints](api-endpoints.md)
- [CLI Reference](cli.md)
