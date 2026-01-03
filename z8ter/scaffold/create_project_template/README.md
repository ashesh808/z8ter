# Z8ter Starter

A minimal starter template for building web apps with **Z8ter (Starlette + Jinja2 + HTMX-friendly)**, **TypeScript**, and **Tailwind v4 + DaisyUI**.

* Server: Python (ASGI/Starlette) via **Z8ter**
* UI: Jinja templates (SSR) with optional per‑page TS modules
* Styling: Tailwind v4 + DaisyUI
* DX: One command to run server + CSS + TS watchers

---

## Quickstart

### 1) Prerequisites

* **Python** 3.10+ (3.11+ recommended)
* **uv** — fast Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
* **Node.js** 18+ and **npm**
* macOS, Linux, or Windows (PowerShell)

### 2) Clone this template

```bash
# Option A: Use GitHub “Use this template” → create repo → then:
git clone https://github.com/<your-username>/<your-new-repo>.git
cd <your-new-repo>

# Option B: Direct clone this repo (for quick testing)
git clone https://github.com/ashesh808/z8ter-starter myapp
cd myapp
```

### 2) Python setup

```bash
# Install dependencies with uv (recommended)
uv sync

# Or using pip (alternative)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3) Node setup

```bash
npm install
```

### 4) Run everything (server + CSS + TS)

```bash
npm run dev
```

Open your browser to:

* App: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* Hello API: [http://127.0.0.1:8000/api/hello/](http://127.0.0.1:8000/api/hello/)  (see “API endpoints” below)

> The `dev` script runs 3 processes concurrently:
>
> * **CSS**: Tailwind CLI → `static/css/output.css`
> * **TS**: TypeScript compiler → `static/js/...`
> * **Server**: `z8 run dev` (Z8ter dev server with reload)

---

## What’s inside

```
api/
  __init__.py
  hello.py                  # class-based API, returns JSON
src/css/
  app.css                   # Tailwind v4 + DaisyUI + @source globs
ts/
  app.ts                    # page loader (dynamic imports)
  page/
    index.ts                # “/” page script
    about.ts                # “/about” page script
views/
  app/base.jinja            # base layout; embeds /static/js/app.js
  home.html                 # SSR page for "/"
  about.html                # SSR page for "/about"
static/
  css/                      # build output (Tailwind)
  js/                       # build output (TypeScript)
  img/
  favicon/
.gitignore
package.json
tsconfig.json
```

### How pages work

* Server renders a view (e.g., `views/home.html`) using `base.jinja`.
* `base.jinja` sets `<body data-page="{{ page_id }}">`.
* `ts/app.ts` reads `data-page` and **dynamically imports** `/static/js/pages/<pageId>.js`.

  * Example: Home page → `pageId="home"` → loads `/static/js/pages/home.js`.
  * We also load `common.js` if present for site‑wide code.

> In the starter, we wire `index` and `about` as examples. When you add a new view, create a matching `ts/page/<name>.ts`.

---

## API endpoints

`api/hello.py` defines a class‑based API with Z8ter’s `API` helper:

```python
from z8ter.api import API
from z8ter.responses import JSONResponse
from z8ter.requests import Request

class Hello(API):
    @API.endpoint("GET", "/")
    async def send_hello(self, request: Request) -> JSONResponse:
        return JSONResponse({"message": "Hello from the API!"}, 200)
```

By default (given Z8ter’s route builders), this mounts at **`/api/hello/`**.
Test it:

```bash
curl http://127.0.0.1:8000/api/hello/
# {"message":"Hello from the API!"}
```

---

## Build for production

```bash
# 1) Build static assets
npm run build
#   - Tailwind → static/css/output.css
#   - TypeScript → static/js/...

# 2) Run the server (one of):
uv run z8 run     # or `uv run z8 run --host 0.0.0.0 --port 8000`
# or uvicorn directly if you expose your ASGI app
# uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Deploy behind Nginx/Caddy/Traefik as you normally would for an ASGI app.

---

## Customize

* **Add a new page**

  1. Create `views/<name>.html` (extends `app/base.jinja`)
  2. Add `ts/page/<name>.ts` (export default function)
  3. Link to it from your templates

* **Add site‑wide JS**
  Create `ts/page/common.ts`. It will auto‑load for all pages.

* **Add styles**
  Edit `src/css/app.css`. Tailwind v4 + DaisyUI are pre‑enabled.

* **Add new API**
  Create another API class in `api/…` similar to `Hello` and rely on Z8ter’s route builder (already integrated in the framework).