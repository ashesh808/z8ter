# React Components (Web Islands)

Z8ter uses an "islands architecture" for frontend interactivity. React components are wrapped as Web Components (Custom Elements), allowing you to drop interactive widgets into server-rendered HTML.

## The Islands Pattern

Instead of a full single-page application (SPA), Z8ter renders pages on the server and sprinkles in interactive "islands" where needed:

```html
<!-- Server-rendered HTML -->
<header>
    <h1>Welcome</h1>
    <z8-theme-toggle></z8-theme-toggle>  <!-- Interactive island -->
</header>

<main>
    <p>Static content...</p>
    <z8-clock></z8-clock>  <!-- Interactive island -->
</main>
```

Benefits:
- **Fast initial load**: HTML is ready immediately
- **Progressive enhancement**: Works without JavaScript
- **Targeted interactivity**: JavaScript only where needed
- **SEO-friendly**: Content is server-rendered

## Project Setup

### File Structure

```
src/
└── ts/
    ├── app.ts                  # Entry point
    ├── pages/                  # Page-specific modules
    │   ├── common.ts
    │   └── index.ts
    └── ui-components/          # React Web Components
        ├── z8-clock.tsx
        ├── z8-theme-toggle.tsx
        └── z8-copy-button.tsx
```

### Dependencies

Your `package.json` should include:

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

### Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  build: {
    manifest: true,
    rollupOptions: {
      input: 'src/ts/app.ts',
    },
    outDir: 'static/js',
  },
  base: '/static/js',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src/ts'),
    },
  },
})
```

## Creating a React Web Component

### Basic Pattern

```tsx
// src/ts/ui-components/z8-greeting.tsx
import React from 'react'
import { createRoot, Root } from 'react-dom/client'

// 1. Define your React component
interface GreetingProps {
  name: string
}

const Greeting: React.FC<GreetingProps> = ({ name }) => {
  return (
    <div className="greeting">
      <h2>Hello, {name}!</h2>
    </div>
  )
}

// 2. Create the Web Component wrapper
class Z8GreetingElement extends HTMLElement {
  private root: Root | null = null

  // Declare which attributes to observe
  static get observedAttributes() {
    return ['name']
  }

  connectedCallback() {
    // Called when element is added to DOM
    this.root = createRoot(this)
    this.render()
  }

  disconnectedCallback() {
    // Called when element is removed from DOM
    this.root?.unmount()
  }

  attributeChangedCallback() {
    // Called when observed attributes change
    this.render()
  }

  private render() {
    if (!this.root) return

    const name = this.getAttribute('name') || 'World'

    this.root.render(<Greeting name={name} />)
  }
}

// 3. Register the custom element
customElements.define('z8-greeting', Z8GreetingElement)
```

### Usage in Templates

```jinja
{% extends "base.jinja" %}

{% block content %}
<div class="container">
    <z8-greeting name="Alice"></z8-greeting>
    <z8-greeting name="{{ user.name }}"></z8-greeting>
</div>
{% endblock %}
```

## Example Components

### Interactive Clock

```tsx
// src/ts/ui-components/z8-clock.tsx
import React, { useState, useEffect } from 'react'
import { createRoot, Root } from 'react-dom/client'

const Clock: React.FC = () => {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date())
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  return (
    <time className="clock" dateTime={time.toISOString()}>
      {time.toLocaleTimeString()}
    </time>
  )
}

class Z8ClockElement extends HTMLElement {
  private root: Root | null = null

  connectedCallback() {
    this.root = createRoot(this)
    this.root.render(<Clock />)
  }

  disconnectedCallback() {
    this.root?.unmount()
  }
}

customElements.define('z8-clock', Z8ClockElement)
```

### Theme Toggle

```tsx
// src/ts/ui-components/z8-theme-toggle.tsx
import React, { useState, useEffect } from 'react'
import { createRoot, Root } from 'react-dom/client'

type Theme = 'light' | 'dark'

const ThemeToggle: React.FC = () => {
  const [theme, setTheme] = useState<Theme>(() => {
    // Check localStorage or system preference
    const saved = localStorage.getItem('theme') as Theme
    if (saved) return saved

    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggle = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'))
  }

  return (
    <button
      onClick={toggle}
      className="theme-toggle"
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  )
}

class Z8ThemeToggleElement extends HTMLElement {
  private root: Root | null = null

  connectedCallback() {
    this.root = createRoot(this)
    this.root.render(<ThemeToggle />)
  }

  disconnectedCallback() {
    this.root?.unmount()
  }
}

customElements.define('z8-theme-toggle', Z8ThemeToggleElement)
```

### Copy Button

```tsx
// src/ts/ui-components/z8-copy-button.tsx
import React, { useState } from 'react'
import { createRoot, Root } from 'react-dom/client'

interface CopyButtonProps {
  text: string
  label?: string
  copiedLabel?: string
}

const CopyButton: React.FC<CopyButtonProps> = ({
  text,
  label = 'Copy',
  copiedLabel = 'Copied!'
}) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <button
      onClick={handleCopy}
      className={`copy-button ${copied ? 'copied' : ''}`}
    >
      {copied ? copiedLabel : label}
    </button>
  )
}

class Z8CopyButtonElement extends HTMLElement {
  private root: Root | null = null

  static get observedAttributes() {
    return ['text', 'label', 'copied-label']
  }

  connectedCallback() {
    this.root = createRoot(this)
    this.render()
  }

  disconnectedCallback() {
    this.root?.unmount()
  }

  attributeChangedCallback() {
    this.render()
  }

  private render() {
    if (!this.root) return

    this.root.render(
      <CopyButton
        text={this.getAttribute('text') || ''}
        label={this.getAttribute('label') || undefined}
        copiedLabel={this.getAttribute('copied-label') || undefined}
      />
    )
  }
}

customElements.define('z8-copy-button', Z8CopyButtonElement)
```

### API Data Fetcher

```tsx
// src/ts/ui-components/z8-api-widget.tsx
import React, { useState, useEffect } from 'react'
import { createRoot, Root } from 'react-dom/client'

interface ApiWidgetProps {
  endpoint: string
}

const ApiWidget: React.FC<ApiWidgetProps> = ({ endpoint }) => {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const response = await fetch(endpoint)
        const json = await response.json()
        setData(json)
      } catch (err) {
        setError('Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [endpoint])

  if (loading) return <div className="loading">Loading...</div>
  if (error) return <div className="error">{error}</div>

  return (
    <div className="api-widget">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  )
}

class Z8ApiWidgetElement extends HTMLElement {
  private root: Root | null = null

  static get observedAttributes() {
    return ['endpoint']
  }

  connectedCallback() {
    this.root = createRoot(this)
    this.render()
  }

  disconnectedCallback() {
    this.root?.unmount()
  }

  attributeChangedCallback() {
    this.render()
  }

  private render() {
    if (!this.root) return

    const endpoint = this.getAttribute('endpoint')
    if (!endpoint) return

    this.root.render(<ApiWidget endpoint={endpoint} />)
  }
}

customElements.define('z8-api-widget', Z8ApiWidgetElement)
```

## Registering Components

Import your components in the main entry point:

```typescript
// src/ts/app.ts

// Import all UI components
import './ui-components/z8-clock'
import './ui-components/z8-theme-toggle'
import './ui-components/z8-copy-button'
import './ui-components/z8-api-widget'

// Page module loader
const pageModules = import.meta.glob<{ default?: (ctx: PageCtx) => void }>(
  './pages/**/*.ts'
)

interface PageCtx {
  pageId: string
  id: string
  body: HTMLElement
}

async function initPage() {
  const body = document.body
  const pageId = body.dataset.page || 'index'
  const id = `page-${pageId}`

  const ctx: PageCtx = { pageId, id, body }

  // Always run common module
  const commonModule = await import('./pages/common')
  commonModule.default?.(ctx)

  // Load page-specific module
  const modulePath = `./pages/${pageId}.ts`
  if (modulePath in pageModules) {
    const module = await pageModules[modulePath]()
    module.default?.(ctx)
  }
}

document.addEventListener('DOMContentLoaded', initPage)
```

## Page-Specific JavaScript

For page-specific logic that isn't a reusable component:

```typescript
// src/ts/pages/dashboard.ts

interface PageCtx {
  pageId: string
  id: string
  body: HTMLElement
}

export default function initDashboard(ctx: PageCtx) {
  console.log('Dashboard page initialized')

  // Add page-specific event listeners
  const refreshBtn = document.getElementById('refresh-data')
  refreshBtn?.addEventListener('click', async () => {
    const response = await fetch('/api/dashboard/stats')
    const data = await response.json()
    updateStats(data)
  })
}

function updateStats(data: any) {
  // Update DOM with new data
}
```

## Passing Data from Server

### Via Attributes

```jinja
<z8-user-card
  user-id="{{ user.id }}"
  name="{{ user.name }}"
  avatar="{{ user.avatar_url }}"
></z8-user-card>
```

### Via Script Tags

```jinja
<script type="application/json" id="page-data">
{{ page_data | tojson }}
</script>

<z8-data-widget data-source="#page-data"></z8-data-widget>
```

```tsx
// In your component
const dataEl = document.querySelector(this.getAttribute('data-source'))
const data = JSON.parse(dataEl?.textContent || '{}')
```

### Via Data Attributes

```jinja
<div id="app-config"
     data-api-base="{{ config.api_base }}"
     data-user-id="{{ user.id }}">
</div>
```

## Styling Components

### Scoped Styles

Use CSS modules or styled-components:

```tsx
// Using inline styles
const Button: React.FC = () => (
  <button style={{
    padding: '0.5rem 1rem',
    backgroundColor: 'var(--primary)',
    color: 'white',
    border: 'none',
    borderRadius: '4px'
  }}>
    Click me
  </button>
)
```

### Global CSS

Add styles in your CSS entry point:

```css
/* src/css/app.css */

z8-clock {
  display: inline-block;
  font-family: monospace;
  font-size: 1.25rem;
}

z8-theme-toggle button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.5rem;
}

z8-copy-button .copied {
  color: green;
}
```

### Using Tailwind

```tsx
const Card: React.FC<{ title: string }> = ({ title }) => (
  <div className="bg-white rounded-lg shadow-md p-6">
    <h3 className="text-xl font-bold text-gray-800">{title}</h3>
  </div>
)
```

## Best Practices

### 1. Keep Components Small

Each component should do one thing well:

```tsx
// Good: Single responsibility
<z8-like-button post-id="123"></z8-like-button>
<z8-share-button url="/posts/123"></z8-share-button>

// Avoid: Too many responsibilities
<z8-social-actions post-id="123" enable-likes enable-shares enable-comments>
```

### 2. Use Progressive Enhancement

Components should enhance, not replace, content:

```jinja
<!-- Content is visible without JS -->
<div class="counter">
    <span>Likes: {{ post.likes }}</span>
    <!-- Enhanced with JS -->
    <z8-like-button post-id="{{ post.id }}" initial="{{ post.likes }}">
    </z8-like-button>
</div>
```

### 3. Handle Loading States

```tsx
const DataWidget: React.FC = () => {
  const [loading, setLoading] = useState(true)

  if (loading) {
    return <div className="skeleton">Loading...</div>
  }

  return <div>...</div>
}
```

### 4. Clean Up Resources

Always clean up in `disconnectedCallback`:

```tsx
class Z8TimerElement extends HTMLElement {
  private root: Root | null = null
  private interval: number | null = null

  connectedCallback() {
    this.root = createRoot(this)
    this.render()
    this.interval = setInterval(() => this.render(), 1000)
  }

  disconnectedCallback() {
    if (this.interval) clearInterval(this.interval)
    this.root?.unmount()
  }
}
```

## Development Workflow

### Running Vite Dev Server

For HMR (Hot Module Replacement):

```bash
# Terminal 1: Python server
z8 run dev

# Terminal 2: Vite dev server
npm run dev
```

Set the `VITE_DEV_SERVER` environment variable:

```env
VITE_DEV_SERVER=http://localhost:5173
```

### Building for Production

```bash
npm run build
```

This creates optimized assets in `static/js/` with a manifest file.

## Next Steps

- [Authentication](authentication.md) - Secure your application
- [Configuration](configuration.md) - Environment and settings
- [CLI Reference](cli.md) - Command-line tools
