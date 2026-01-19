# Z8ter Framework - Problems & Gaps Analysis

This document identifies gaps between Z8ter's current state and its goal of being the ideal scaffolding for SaaS micro-apps that minimize time-to-cash.

---

## 1. No Database Integration

**Current State:** Only in-memory repositories exist (`InMemorySessionRepo`, `InMemoryUserRepo`). The framework deliberately avoids database dependencies.

**Why This Is A Problem:**

- Data is lost on every restart - unusable for any real application
- Developers must implement their own database layer from scratch before anything works
- A coding agent cannot scaffold a working app without first writing database code
- Contradicts the "minimum commands" goal - should work out of the box

**What's Needed:**

- Default SQLite database with migrations
- Pre-built `SQLiteSessionRepo` and `SQLiteUserRepo` implementations
- Simple configuration: just set `DATABASE_URL` or use default `sqlite:///app.db`
- Optional: easy upgrade path to PostgreSQL for production

---

## 2. No Payment/Stripe Integration

**Current State:** Empty `billing/` module exists but contains no implementation.

**Why This Is A Problem:**

- Payments are the core of "time-to-cash" - without them, there's no cash
- Every SaaS needs subscriptions, one-time payments, or usage-based billing
- Developers must research and implement Stripe integration themselves
- No guidance on webhook handling, subscription states, or customer portal

**What's Needed:**

- Stripe SDK integration with configuration via environment variables
- Pre-built billing models: Customer, Subscription, Payment
- Webhook endpoint for Stripe events (payment_intent.succeeded, subscription.updated, etc.)
- Subscription management: create, cancel, update
- Customer portal redirect
- Usage tracking helpers for metered billing
- CLI command: `z8 setup stripe` to configure keys and webhook secret

---

## 3. No Dockerfile or Deployment Configuration

**Current State:** No Docker files exist. Framework runs via Uvicorn but deployment is entirely manual.

**Why This Is A Problem:**

- Modern deployment expects containerization
- Without a Dockerfile, deploying to Railway, Fly.io, Render, or any cloud platform requires manual configuration
- Developers must figure out Python version, dependencies, static file serving, and production settings
- Contradicts "ready to deploy" goal

**What's Needed:**

- Production-ready `Dockerfile` in scaffold template
- `docker-compose.yml` for local development with services (db, redis, etc.)
- `.dockerignore` to exclude dev files
- Health check endpoint (`/health`)
- Static file serving configuration for production
- Environment-based configuration (dev vs prod)

---

## 4. No Email/Transactional Email Support

**Current State:** No email functionality exists. Registration and login work but cannot send emails.

**Why This Is A Problem:**

- Cannot implement "forgot password" without email
- Cannot send welcome emails, receipts, or notifications
- Email verification for new accounts is impossible
- Essential SaaS communication channel is missing

**What's Needed:**

- Email service abstraction with pluggable providers (SMTP, SendGrid, Resend, Postmark)
- Default SMTP configuration
- Pre-built transactional email templates:
  - Welcome email
  - Password reset
  - Email verification
  - Payment receipt
  - Subscription confirmation/cancellation
- Async email sending (background task)
- CLI command: `z8 setup email` to configure provider

---

## 5. Incomplete Authentication

**Current State:** Basic session-based auth with password hashing exists. No OAuth or password recovery.

**Why This Is A Problem:**

- "Login with Google" is expected by users - reduces friction significantly
- No forgot password flow means locked-out users have no recourse
- No email verification means fake accounts can be created
- Missing security features that users expect from any SaaS

**What's Needed:**

- **OAuth Providers:**
  - Google OAuth (priority)
  - Optional: GitHub, Apple
  - Pre-built routes: `/auth/google`, `/auth/google/callback`
- **Password Reset Flow:**
  - `/forgot-password` page with email input
  - Secure token generation with expiry
  - `/reset-password?token=xxx` page
  - Email template for reset link
- **Email Verification:**
  - Send verification email on registration
  - `/verify-email?token=xxx` endpoint
  - Resend verification option
- **Session Security:**
  - Rate limiting on login attempts
  - Account lockout after failed attempts
  - Session invalidation on password change

---

## 6. No Admin Portal

**Current State:** No admin functionality exists.

**Why This Is A Problem:**

- Cannot manage users without database queries
- Cannot view/cancel subscriptions without Stripe dashboard
- No visibility into application state
- Every SaaS needs basic admin capabilities for support and operations

**What's Needed:**

- Protected `/admin` routes (role-based access)
- User management:
  - List users with search/filter
  - View user details
  - Disable/enable accounts
  - Impersonate user (for debugging)
- Subscription management:
  - View subscriptions
  - Cancel/refund from admin
  - Extend trials
- Basic analytics:
  - User signups over time
  - Active users
  - Revenue metrics (from Stripe)

---

## 7. No Security Baseline

**Current State:** Some security exists (Argon2 passwords, secure cookies) but no comprehensive security configuration.

**Why This Is A Problem:**

- Missing CSRF protection on forms
- No rate limiting
- No security headers (CSP, HSTS, X-Frame-Options)
- No input validation framework
- Developers must research and implement security themselves

**What's Needed:**

- CSRF middleware enabled by default
- Rate limiting middleware (configurable per-route)
- Security headers middleware:
  - Content-Security-Policy
  - Strict-Transport-Security
  - X-Content-Type-Options
  - X-Frame-Options
- Input validation helpers (Pydantic integration)
- SQL injection protection (via ORM/parameterized queries)
- XSS protection in templates (Jinja2 autoescaping - verify enabled)

---

## 8. Landing Page Needs SaaS Focus

**Current State:** Basic landing page template exists but is generic.

**Why This Is A Problem:**

- SaaS landing pages have specific patterns: hero, features, pricing, testimonials, CTA
- No pricing table component
- No integration with Stripe products for dynamic pricing
- Developers must design and build conversion-focused pages from scratch

**What's Needed:**

- SaaS-focused landing page template with:
  - Hero section with CTA
  - Feature highlights
  - Pricing table (integrated with Stripe products)
  - Testimonials section
  - FAQ section
  - Footer with legal links
- Pre-built components:
  - `<PricingTable>` that reads from Stripe
  - `<FeatureCard>`
  - `<Testimonial>`
- Legal page templates:
  - Privacy Policy (template with placeholders)
  - Terms of Service (template with placeholders)

---

## 9. CLI Lacks Essential Commands

**Current State:** CLI has `new`, `run`, `create_page`, `create_api` commands.

**Why This Is A Problem:**

- No database migration commands
- No way to set up third-party integrations
- No deployment helpers
- Coding agents need clear, documented commands to scaffold apps

**What's Needed:**

- `z8 db init` - Initialize database with tables
- `z8 db migrate` - Run migrations
- `z8 db seed` - Seed with sample data
- `z8 setup stripe` - Configure Stripe integration
- `z8 setup email` - Configure email provider
- `z8 setup oauth google` - Configure Google OAuth
- `z8 build` - Build frontend assets for production
- `z8 deploy` - Deploy helpers (generate Dockerfile, fly.toml, etc.)
- `z8 check` - Validate configuration and dependencies

---

## 10. Documentation Gaps

**Current State:** README exists but lacks comprehensive guidance.

**Why This Is A Problem:**

- Coding agents need clear documentation to understand capabilities
- Developers cannot discover features without reading source code
- No quickstart guide for common tasks
- No architecture documentation explaining the builder pattern

**What's Needed:**

- Quickstart guide: "Build a SaaS in 10 minutes"
- Configuration reference (all environment variables)
- Authentication guide (implementing repos, OAuth setup)
- Payments guide (Stripe setup, webhooks, subscriptions)
- Deployment guide (Docker, Railway, Fly.io)
- API reference (all classes and functions)
- Examples: common SaaS patterns

---

## 11. No Background Task Support

**Current State:** No task queue or background job system.

**Why This Is A Problem:**

- Email sending should be async
- Webhook processing should be async
- Long-running operations block requests
- No way to schedule recurring tasks (subscription renewals, cleanup)

**What's Needed:**

- Simple background task system (could use `asyncio` tasks for simple cases)
- Optional integration with task queues (Celery, RQ, or simpler alternatives)
- Scheduled task support for cron-like jobs

---

## 12. Testing Infrastructure Missing

**Current State:** No testing utilities or example tests.

**Why This Is A Problem:**

- Developers must figure out how to test Z8ter apps
- No test client configuration
- No fixtures for authenticated requests
- No mocks for external services (Stripe, email)

**What's Needed:**

- Test client setup guide
- Pytest fixtures for:
  - Authenticated user sessions
  - Stripe mock/test mode
  - Email capture
  - Database setup/teardown
- Example test files in scaffold

---

## Priority Order for Implementation

Based on the "time-to-cash" goal, recommended priority:

1. **SQLite Database** - Nothing works without persistence
2. **Stripe Payments** - Core of monetization
3. **Transactional Emails** - Required for password reset and receipts
4. **Complete Auth** (Google OAuth, forgot password) - User expectations
5. **Dockerfile** - Deployment readiness
6. **Security Baseline** - Production requirements
7. **Admin Portal** - Operational necessity
8. **Landing Page Components** - Conversion optimization
9. **CLI Commands** - Developer experience
10. **Documentation** - Adoption and AI-agent usability
11. **Background Tasks** - Scalability
12. **Testing Infrastructure** - Quality assurance

---

## Summary

Z8ter has a solid foundation with its builder pattern, authentication middleware, and CLI scaffolding. However, it currently requires significant development effort before a SaaS can actually launch and make money. The framework provides structure but not substance for the critical paths: data persistence, payments, and user communication.

To achieve the goal of "minimum commands to a deployed, monetizable app," Z8ter needs batteries-included defaults for database, payments, and email, while keeping the pluggable architecture for teams that need customization.
