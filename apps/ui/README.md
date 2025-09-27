# AI Invoice Console UI

Minimalist, Costa Rica–inspired React + Tailwind dashboard for the AI Invoice platform. The console embraces an original "Aurora" shell with custom gradients, card auras, and typography that keep the experience unmistakably ours while shipping mocked data so it can be explored offline and later wired to live APIs.

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

The UI uses Indigo `#3F51B5` as the primary color with bespoke Costa Rica accents (`#002B7F`, `#CE1126`, and our sunrise `#F4A71D`) while supporting light, dark, and system themes. Preferences persist via `localStorage`, animate the gradient theme toggle, and automatically react to OS theme changes.

## Mock data

All dashboards, tables, and workflows use static mocks under `src/data/mockData.ts`. Swap these with live fetches (e.g., `/invoices`, `/vendors`, `/approvals`) once backend endpoints are ready.

## Design language

- **Aurora backdrop:** Layered gradients and wave motifs in `BrandBackdrop.tsx` reference Costa Rican skies and coastlines without reusing competitor layouts.
- **Signature navigation:** Sidebar tiles, accent pills, and typography create a "PuraFlow" voice distinct from any reference inspiration.
- **Immersive cards:** `Card.tsx` introduces custom aura glows and tricolor footers so data blocks feel handcrafted.

These patterns make the console visually unique while staying within our minimalist brand direction.
