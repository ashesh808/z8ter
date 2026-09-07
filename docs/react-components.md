# Interactive Islands

Z8ter renders HTML with Jinja and lets you add focused client-side components. The generated starter uses **Solid custom elements** through `solid-element`, not React. This page keeps its existing URL for older links.

The server-rendered content can be displayed before components initialize. Interactive controls still require JavaScript; fallback content and accessibility are the application's responsibility.

## How page modules load

The generated base template includes:

```jinja
<body data-page="{{ page_id }}">
  {% block content %}{% endblock %}
  {{ vite_script_tag("src/ts/app.ts") }}
</body>
```

The starter's `src/ts/app.ts` reads `document.body.dataset.page`, then uses Vite's dynamic import map to load `src/ts/pages/PAGE.ts`. Dots become directories: `app.dashboard` selects `pages/app/dashboard.ts`.

The loader attempts `pages/common.ts` first and then the page-specific module. A missing module is skipped with a console warning. If a module exports a default initializer, it receives `{ pageId, id, body }`; in the current loader, `id` equals the module's page ID, without a `page-` prefix.

## Create a Solid custom element

The starter already includes `solid-js`, `solid-element`, and the Solid Vite plugin. Add this illustrative component:

```tsx
// src/ts/ui-components/demo-counter.tsx
import { customElement, noShadowDOM } from "solid-element";
import { createSignal } from "solid-js";

customElement("demo-counter", {}, () => {
  noShadowDOM();
  const [count, setCount] = createSignal(0);
  return (
    <button type="button" onClick={() => setCount((value) => value + 1)}>
      Clicks: {count()}
    </button>
  );
});
```

Import it in the page that needs it:

```typescript
// src/ts/pages/hello.ts
import "@/ui-components/demo-counter";

export default function init(): void {}
```

Then use the tag in the matching Jinja template:

```jinja
{# templates/pages/hello.jinja #}
{% extends "base.jinja" %}
{% block content %}
  <h1>{{ title }}</h1>
  <demo-counter></demo-counter>
{% endblock %}
```

The Python view should live in `endpoints/views/hello.py` so its `page_id` is `hello`. The component module registers the custom element when imported. This is client-side mounting inside a server-rendered page, not automatic hydration of a server-rendered Solid or React tree.

`noShadowDOM()` lets the element use the page's existing styles. If you choose shadow DOM, provide styles inside that shadow root. Use a hyphen in custom-element names.

## Attributes and server data

`solid-element` can declare default props that map to element attributes:

```tsx
// src/ts/ui-components/demo-greeting.tsx
import { customElement, noShadowDOM } from "solid-element";

customElement("demo-greeting", { name: "World" }, (props) => {
  noShadowDOM();
  return <p>Hello, {props.name}!</p>;
});
```

```jinja
<demo-greeting name="{{ display_name }}"></demo-greeting>
```

Keep normal template escaping enabled. For complex values, serialize deliberately and parse on the client; do not insert untrusted HTML with `innerHTML` or bypass escaping with `safe`.

## Page-specific behavior

A page module can also contain ordinary TypeScript without any component framework:

```typescript
// src/ts/pages/about.ts
export default function init({ body }: { body: HTMLElement }): void {
  const button = body.querySelector<HTMLButtonElement>("[data-show-details]");
  const details = body.querySelector<HTMLElement>("[data-details]");
  button?.addEventListener("click", () => {
    if (details) details.hidden = !details.hidden;
  });
}
```

The loader runs after `DOMContentLoaded`. Put shared imports in `pages/common.ts` when you want them on every page rather than importing every component globally.

## API calls

A component can call any endpoint using `fetch`; the bundled `z8-ping` component demonstrates a request to `/api/hello`. Handle loading, failures, and response validation in your UI.

For unsafe methods protected by CSRF, include a valid `X-CSRF-Token` header or a `csrf_token` form field. The CSRF cookie is HttpOnly; expose the token from the server's template context instead of trying to read that cookie in JavaScript. See [Security](security.md).

## Build and development

```bash
npm ci
npm run typecheck
npm run build
```

The starter builds Tailwind to `static/css/output.css` and Vite assets to `static/js`, including `.vite/manifest.json`. Its combined watcher command is:

```bash
uv run -- npm run dev
```

That command runs the Python server plus CSS and JS build watchers. It is not a Vite HMR server; keep `VITE_DEV_SERVER` unset unless you configure that separate workflow. See [CLI Reference](cli.md).

## Using React instead

Z8ter's Python routing and Jinja rendering do not require a particular browser framework. React integration is an application choice: configure a React-compatible Vite plugin and TypeScript settings, install the matching React packages, and register/mount your component wrappers. The generated Solid setup cannot compile React JSX unchanged. Z8ter does not automatically create React roots or manage their cleanup.

## Next steps

- [Views & Pages](views.md)
- [API Endpoints](api-endpoints.md)
- [Project Structure](project-structure.md)
