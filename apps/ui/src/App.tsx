import { useMemo, useState } from 'react';
import { ThemeProvider } from './hooks/useTheme';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { BrandBackdrop } from './components/BrandBackdrop';
import { DashboardSection } from './sections/DashboardSection';
import { InvoiceViewerSection } from './sections/InvoiceViewerSection';
import { VendorListSection } from './sections/VendorListSection';
import { ReportsSection } from './sections/ReportsSection';
import { ApprovalsSection } from './sections/ApprovalsSection';
import { SettingsSection } from './sections/SettingsSection';

export type AppSectionKey =
  | 'dashboard'
  | 'invoices'
  | 'vendors'
  | 'reports'
  | 'approvals'
  | 'settings';

type SectionItem = {
  id: AppSectionKey;
  label: string;
  description: string;
  component: JSX.Element;
};

const useSections = (): SectionItem[] =>
  useMemo(
    () => [
      {
        id: 'dashboard',
        label: 'Dashboard',
        description: 'Pulse of your invoice operations at a glance.',
        component: <DashboardSection />
      },
      {
        id: 'invoices',
        label: 'Invoice Viewer',
        description: 'Details, line items, and actions for the current invoice.',
        component: <InvoiceViewerSection />
      },
      {
        id: 'vendors',
        label: 'Vendors',
        description: 'Searchable directory of suppliers with contact details.',
        component: <VendorListSection />
      },
      {
        id: 'reports',
        label: 'Reports',
        description: 'Download-ready summaries and insights for finance teams.',
        component: <ReportsSection />
      },
      {
        id: 'approvals',
        label: 'Approvals',
        description: 'Fast approval workflow with delightful micro-animations.',
        component: <ApprovalsSection />
      },
      {
        id: 'settings',
        label: 'Settings',
        description: 'Theme controls, notifications, and workspace preferences.',
        component: <SettingsSection />
      }
    ],
    []
  );

const AppShell = () => {
  const sections = useSections();
  const [active, setActive] = useState<AppSectionKey>('dashboard');
  const current = sections.find((section) => section.id === active) ?? sections[0];

  return (
    <div className="relative flex h-full min-h-screen bg-transparent text-slate-700 dark:text-slate-200">
      <BrandBackdrop />
      <Sidebar
        sections={sections.map(({ id, label }) => ({ id, label }))}
        active={active}
        onSelect={setActive}
      />
      <div className="relative z-10 flex flex-1 flex-col">
        <TopBar title={current.label} description={current.description} />
        <main className="flex-1 overflow-y-auto px-6 pb-12 pt-6 sm:px-10">
          <div className="mx-auto max-w-6xl space-y-8">{current.component}</div>
        </main>
      </div>
    </div>
  );
};

const App = () => (
  <ThemeProvider>
    <AppShell />
  </ThemeProvider>
);

export default App;
