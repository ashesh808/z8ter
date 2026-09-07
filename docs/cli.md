# CLI Reference

The `z8` command is installed with Z8ter. Inside a uv-managed project, prefix commands with `uv run` so they use that project's environment.

```bash
uv run z8 --help
uv run z8 create_page --help
```

## Create a project

```bash
uvx --from z8ter z8 new myapp
cd myapp
uv sync
npm ci
npm run build
uv run z8 run dev
```

`z8 new PROJECT_NAME` copies the packaged starter into a new or empty directory. It does not install dependencies. The starter includes Python views/APIs, Jinja templates, a uv project, npm lockfile, Solid custom elements, and Tailwind/Vite configuration.

Exit codes are `0` for success, `2` for an occupied/non-directory target, `3` for a missing packaged template, and `4` for a copy error.

## Generate pages and APIs

```bash
uv run z8 create_page products
uv run z8 create_page app/settings
uv run z8 create_api products
uv run z8 create_api admin/reports
```

For `create_page products`, the generator writes:

```text
endpoints/views/products.py
templates/pages/products.jinja
content/products.yaml
src/ts/pages/products.ts
```

The view subclasses `View`; the template extends `base.jinja`; YAML contains a `headings` mapping; the TypeScript file exports an empty initializer. Edit these generated files to implement your page.

`create_api products` writes `endpoints/api/products.py` with a decorated sample handler. It does not generate a database model or a complete CRUD implementation.

Names are normalized to lowercase and may contain nested path segments. Existing files are skipped. The Python functions accept `force=True` for deliberate replacement; the command-line parser does not expose a `--force` flag for page/API generation.

## Run the Python server

```bash
uv run z8 run dev
uv run z8 run prod
```

Omitting the mode selects **prod**, not dev. The CLI uses port 8000 and these mode defaults:

- `dev`: `127.0.0.1`, reload enabled.
- `prod`: `127.0.0.1`, reload disabled.
- `LAN`: the detected LAN address, reload enabled.
- `WAN`: `0.0.0.0`, reload enabled.

LAN/WAN are development convenience modes, not a production-hardening switch. For a container or a custom port without reload, run Uvicorn directly against the generated ASGI object:

```bash
Z8TER_DEBUG=false uv run uvicorn main:asgi_app --host 0.0.0.0 --port 8000
```

In 0.3.1, `z8 run` uses `z8ter.cli.run_server:load_app`. It imports `main`, reuses callable `main.asgi_app` or `main.app` in that order, and otherwise calls `main.app_builder.build()`. Reusing the built app preserves middleware and services instead of consuming the builder queue twice. Export `Z8TER_APP_FACTORY` only when supplying your own ASGI factory. The CLI also defaults `Z8TER_DEBUG` from the mode before importing the app; an explicit environment value is preserved. `PORT=3000 z8 run dev` does not override the CLI port; use `uv run uvicorn main:asgi_app --port 3000` or the Python `run_server(port=3000)` function.

## Frontend development

The generated `npm run dev` starts CSS watch, Vite build-watch, and the Python server together. With uv, run it through the project environment:

```bash
uv run -- npm run dev
```

Do not also start a second `z8 run dev` process on port 8000. Alternatively, use separate terminals for the individual scripts:

```bash
# Terminal 1
npm run dev:css

# Terminal 2
npm run dev:js

# Terminal 3
uv run z8 run dev
```

This workflow rebuilds files under `static/`; it does not start a Vite HMR server. Keep `VITE_DEV_SERVER` unset. If you choose a Vite dev-server workflow yourself, export its URL before importing the Python app. See [Configuration](configuration.md).

## SQLite commands

The `db` subcommands initialize and inspect the built-in SQLite schema. They are needed when your application uses the bundled database, not for every SSR page.

```bash
uv run z8 db init --url sqlite:////absolute/path/to/app.db
uv run z8 db status --url sqlite:////absolute/path/to/app.db
uv run z8 db reset --url sqlite:////absolute/path/to/app.db
```

`reset` drops and recreates tables. It prompts for `yes`; `--force` skips that prompt. Use it only when you intend to erase the data.

Without `--url`, these commands read `DATABASE_URL` from the process environment, then fall back to the framework default. They do not load your project's `.env` file. The current SQLite parser treats the default `sqlite:///data/app.db` as `/data/app.db`; supply an explicit writable absolute URL.

## Programmatic API

```python
from pathlib import Path
import z8ter
from z8ter.cli.new import new_project
from z8ter.cli.create import create_api, create_page

result = new_project("myapp")
if result == 0:
    z8ter.set_app_dir(Path("myapp").resolve())
    create_page("products")
    create_api("products")
```

The callable names are `new_project`, `create_page`, and `create_api`. There are no public `scaffold_project`, `scaffold_page`, or `scaffold_api` functions.

## Override page/API generator templates

The page/API generator checks a `scaffold_dev` directory relative to the working directory before packaged templates. Use the actual template names:

```text
scaffold_dev/
  create_page_templates/
    view.py.j2
    page.jinja.j2
    page.yaml.j2
    page.ts.j2
  create_api_template/
    api.py.j2
```

Variables use `[[ variable ]]` and blocks use `[% block %]`. This override applies to page/API generation; `z8 new` copies the packaged project template separately.

## Troubleshooting

- Command not found: use `uv run z8 ...` after `uv sync`, or activate the environment where Z8ter is installed.
- Missing Vite manifest: run `npm run build` before serving templates that call `vite_script_tag`.
- Import errors: run from the generated project root and confirm the factory name matches `main.py`.
- Occupied port: choose another port with Uvicorn's `--port` option.

## Next steps

- [Getting Started](getting-started.md)
- [Project Structure](project-structure.md)
- [Views & Pages](views.md)
