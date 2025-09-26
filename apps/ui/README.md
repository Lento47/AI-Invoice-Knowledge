# AI Invoice Console UI

Minimalist dual-theme React + Tailwind dashboard for the AI Invoice platform. The UI ships with mocked data so it can be explored offline while providing a ready structure for wiring real APIs later.

## Prerequisites

- Node.js 18+
- npm 9+

## Getting started

```bash
npm install
npm run dev
```

Then open `http://localhost:5173` in your browser.

To create a production build:

```bash
npm run build
```

> **Note:** The FastAPI service serves the compiled console from `src/api/static/console`. Run the build command before starting the backend so `/portal` can return the React app.

### Project structure

```
apps/ui
├── package.json
├── index.html
├── src
│   ├── App.tsx
│   ├── components
│   ├── data
│   ├── hooks
│   └── sections
├── tailwind.config.js
└── tsconfig.json
```

## Theming

The UI uses Indigo `#3F51B5` as the primary color with Costa Rica accents (`#CE1126` and `#002B7F`) and supports light, dark, and system themes. Preferences persist via `localStorage` and automatically react to OS theme changes.

## Mock data

All dashboards, tables, and workflows use static mocks under `src/data/mockData.ts`. Swap these with live fetches (e.g., `/invoices`, `/vendors`, `/approvals`) once backend endpoints are ready.
