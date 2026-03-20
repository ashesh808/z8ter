# Z8ter Starter

A minimal Z8ter app scaffold with SSR views, decorator-based APIs, Vite,
Tailwind, and TypeScript already wired together.

## Quickstart

```bash
uv sync
npm install
npm run dev
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

If you prefer `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
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
z8 create_page products
z8 create_api users
npm run build
uv run z8 run prod
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## Notes

- `main.py` exposes `app` for plain ASGI servers and `app_builder` for `z8 run`.
- Views live under `endpoints/views/` and map to routes automatically.
- APIs live under `endpoints/api/` and mount under `/api/<name>`.
