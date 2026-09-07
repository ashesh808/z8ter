# Z8ter Starter

A minimal Z8ter app scaffold with SSR views, decorator-based APIs, Vite,
Tailwind, and TypeScript already wired together.

## Quickstart

Use Python 3.10+, Node.js 22.12+ and npm for the frontend toolchain.

```bash
uv sync
npm install
npm run build
uv run npm run dev
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

If you prefer `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm install
npm run build
npm run dev
```

## Project Layout

```text
main.py
endpoints/
  views/
    index.py
    about.py
  api/
    hello.py
templates/
  base.jinja
  pages/
content/
src/
  css/
  ts/
static/
```

`npm run dev` runs three watchers together:

- Tailwind output to `static/css/output.css`
- Vite build/watch for TypeScript assets under `static/js/`
- `z8 run dev` for the backend

## Useful Commands

```bash
uv run z8 create_page products
uv run z8 create_api users
npm run typecheck
npm run build
uv run z8 run prod
uv run uvicorn main:asgi_app --host 0.0.0.0 --port 8000
```

`npm run typecheck` checks TypeScript once; use `npm run typecheck:watch`
for continuous checks while developing.

## Notes

- `main.py` exposes `asgi_app` for ASGI servers and the configured `app` and `app_builder`.
- Views live under `endpoints/views/` and map to routes automatically.
- APIs live under `endpoints/api/` and mount under `/api/<name>`.

The starter uses Solid custom elements for optional interactivity. Database and
authentication setup are optional. Frontend watchers rebuild assets; reload your
browser to see the changes.

For direct Uvicorn deployment, set `Z8TER_DEBUG=false` in the process environment
before importing the app. The `z8 run prod` command selects that default for you.
