# Minimalist Dual-Theme App UI with Indigo & Costa Rica Accents

## Introduction
This proposal outlines a minimalist user interface for an invoice-centric management application that includes Dashboard, Invoice Viewer, Vendor List, Settings, Reports, and Approval Workflow sections. The design emphasizes simplicity, usability, and support for both Light and Dark themes while highlighting an Indigo-driven brand system accented with colors inspired by Costa Rica’s natural palette and national flag.

## Core Sections & Layout

### Dashboard
- Present high-priority KPIs (pending invoices, upcoming due dates, approval counts) using modular cards aligned to a responsive grid.
- Use concise typography and minimalist charts (bar/line) with soft grid lines; accentuate alerts with subtle flag-red highlights.
- Enable drill-down navigation from each card to detailed views while retaining generous whitespace for clarity.

### Invoice Viewer
- Split layout into a summary panel (invoice ID, vendor, dates, totals, status) and detailed line items.
- Employ a clean table with light dividers or alternating row shading, grouping secondary information into collapsible sections.
- Anchor primary actions (Approve, Reject, Next/Previous) in a persistent bar that uses Indigo for the main CTA.

### Vendor List
- Provide a lightweight, searchable table of vendors (Name, Company, Contact, Status) with zebra striping or subtle dividers.
- Surface row-level actions (edit, archive) on hover via simple line icons; highlight the active row with a muted Indigo tint.

### Settings
- Organize options into clear groupings (Profile, Preferences, Notifications, Theme) rendered as cards or segmented lists with ample padding.
- Style toggles, checkboxes, and dropdowns with Indigo active states; expose the Light/Dark/Auto theme switch prominently.

### Reports
- Offer a list or grid of report cards summarizing title, timeframe, and available actions (view, download).
- When displaying analytics, reuse minimalist table styling and restrained charts that emphasize hierarchy through typography and spacing.

### Approval Workflow
- Present an inbox of pending approvals via concise cards or rows showing key invoice metadata and status chips.
- Use color coding carefully: Indigo for neutral actions, a soft green for approved states, and Costa Rica flag red for critical or rejected items.
- Mirror the Invoice Viewer layout in the detailed approval screen with clear CTA buttons and optional comment fields.

## Design Style & Principles
- **Focus on essentials:** Only display elements that support the primary task; avoid decorative graphics that do not aid comprehension.
- **Visual hierarchy:** Guide attention through consistent typographic scale, spacing, and grouping so users can scan effortlessly.
- **Generous whitespace:** Maintain comfortable margins and padding to reinforce the minimalist aesthetic and touch-friendly targets.
- **Flat aesthetics:** Favor flat components with occasional subtle shadows to establish depth without clutter.
- **Typography & iconography:** Use a single sans-serif family with defined weights for headings/body text; pair with a cohesive set of flat line icons accompanied by labels for clarity.

## Dual Light & Dark Mode Strategy
- **Light mode:** Utilize off-white or light neutral backgrounds with dark gray text; apply Indigo to interactive elements and employ gentle shadows for elevation.
- **Dark mode:** Adopt deep charcoal surfaces (#121212 range) with near-white text (#E0E0E0) and adjust Indigo saturation for legibility; lighten divider tones to preserve contrast.
- **Accent handling:** Calibrate accent colors for each theme (slightly softened reds/greens in dark mode) to avoid glare while maintaining brand cues.
- **Theme consistency:** Keep layout, iconography, and typography identical across modes; offer a toggle in Settings plus an Auto option that follows system preference.

## Color Scheme & Branding
- **Primary color:** Indigo (aligned with Costa Rica’s Catalina Blue) drives navigation highlights, primary buttons, and focus states.
- **Neutrals:** Off-whites and soft grays (light mode) plus charcoal tones (dark mode) form ~60% of the palette to sustain minimalism.
- **Accents:** Costa Rica flag red (#CE1126) provides ~10% accent for alerts, destructive actions, and badges; a muted tropical green supports success states and references the natural landscape.
- **Distribution:** Follow the 60-30-10 rule—neutrals (60%), Indigo and related hues (30%), accents (10%)—to maintain visual balance.
- **Guidelines:** Document explicit usage (e.g., Indigo = primary action, red = destructive, green = success) and ensure all color combinations meet WCAG contrast ratios.

## Conclusion
The minimalist dual-theme UI delivers a cohesive, culturally resonant experience that prioritizes clarity and efficiency. Users can swiftly interpret key metrics, inspect invoices, manage vendors, adjust settings, analyze reports, and process approvals without distraction. Consistent patterns, disciplined color usage, and synchronized Light/Dark themes ensure the interface remains intuitive while celebrating the app’s Indigo identity and Costa Rican roots.
