# AI Invoice Console UI

Minimalist dual-theme React + Tailwind dashboard for the AI Invoice platform. The UI ships with mocked data so it can be explored offline while providing a ready structure for wiring real APIs later.

## Prerequisites

- Node.js 18+
- npm 9+

## Getting started

```bash
npm install
cp .env.example .env.local # optional but recommended
npm run dev
```

Then open `http://localhost:5173` in your browser.

## Connecting to the FastAPI backend

1. Start the Python service (from the repository root):

   ```bash
   uv run uvicorn api.main:app --reload --port 8088
   ```

2. Configure the UI with the backend host by editing `.env.local` (copied from `.env.example`). For a default local setup this is
   `VITE_API_BASE_URL=http://localhost:8088`.

3. Once the workspace loads, open **Settings → API access** and paste your `X-API-Key` and `X-License` tokens. The console stores
   them in the browser and automatically includes them with every request.

4. Use the dashboard, invoice viewer, and other sections normally. They now stream live data from the FastAPI endpoints.

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

Legacy mock payloads live under `src/data/mockData.ts` for reference. The hooks in `src/hooks/useWorkspaceData.ts` now call the
FastAPI endpoints by default, so you only need the mocks when working offline.
