# Changelog

## 0.3.1 — 2026-09-06

### Fixes

- Preserve form fields and multipart uploads after CSRF token validation so
  endpoint handlers can read the submitted data.
- Bound CSRF form-token buffering to 8 MiB, including requests without a
  `Content-Length` header. Return HTTP 413 when the limit is exceeded and keep
  stricter application body limits in effect. Configure the limit with
  `AppBuilder.use_csrf(max_form_body_size=...)`.
- Keep uploads using `X-CSRF-Token` streaming through the CSRF middleware,
  subject to application and proxy limits.
- Reuse the application's configured ASGI instance when starting it with
  `z8 run`, preserving templates, security middleware, and health checks.
  Continue to support builder-only projects and `Z8TER_APP_FACTORY` overrides.
- Include the missing About template and page module in generated projects,
  refresh bundled frontend assets, and correct setup commands to build assets
  before starting the development watchers.
- Exclude local `.env` files from source and wheel distributions.

### Maintenance

- Update runtime and frontend dependencies, require a patched Jinja2 release,
  and declare the multipart parser used by form handling.
- Add frontend install, typecheck, build, and dependency-audit checks to CI;
  test Python 3.10–3.14 and check installed dependency compatibility.
- Correct the guides to describe the shipped Solid custom elements, explicit
  feature configuration, actual CLI behavior, and frontend build/watch setup.

### Upgrade notes

- **Starlette 1.6 or newer, below 2.0, is now required.** The PyPI 0.3.0 release
  allowed Starlette below 1.0. Update conflicting dependency pins and review
  application code or extensions that rely on removed Starlette APIs. This
  release does not promise compatibility with Starlette 0.x integrations.
- Jinja2 must be at least 3.1.6 and `python-multipart` at least 0.0.32.
- Form-token uploads over 8 MiB now receive HTTP 413 by default. Increase
  `max_form_body_size`, or provide the CSRF token in `X-CSRF-Token` when the
  endpoint should stream the upload. Other configured limits still apply.
- Use Node.js 22.12+ for the documented frontend workflow. The starter's Vite
  7 toolchain also accepts Node.js 20.19+.
- For a generated app, run `uv sync`, `npm install`, `npm run build`, then
  `uv run npm run dev`. With pip, activate your environment before running
  the equivalent install/build commands and `npm run dev`.
- Existing applications are not rewritten by installing a package update.
  Apply desired starter and configuration changes to your own application.

Z8ter remains a public alpha.
