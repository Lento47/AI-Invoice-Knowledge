import { Card } from '../components/Card';
import { useReportsLibrary } from '../hooks/useWorkspaceData';

export const ReportsSection = () => {
  const { data, status, error, refresh } = useReportsLibrary();
  const reports = data ?? [];
  const isLoading = status === 'loading' && reports.length === 0;

  if (status === 'error' && reports.length === 0) {
    return (
      <Card>
        <div className="flex items-center justify-between gap-4 text-sm text-crRed">
          <span>Unable to load reports: {error}</span>
          <button
            onClick={() => refresh()}
            className="rounded-full border border-crRed/40 px-3 py-1 text-xs font-semibold text-crRed transition hover:bg-crRed/10"
          >
            Retry
          </button>
        </div>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <div className="p-6 text-center text-sm text-slate-500 dark:text-slate-400">Loading reports…</div>
      </Card>
    );
  }

  if (status === 'success' && reports.length === 0) {
    return (
      <Card>
        <div className="p-6 text-center text-sm text-slate-500 dark:text-slate-400">
          No analytics reports have been generated yet.
        </div>
      </Card>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
      {reports.map((report) => (
        <Card key={report.id} title={report.title} eyebrow="Report">
          <p>{report.description}</p>
          <div className="mt-6 flex items-center justify-between text-xs text-slate-400 dark:text-slate-500">
            <span>{report.updated}</span>
            <button className="inline-flex items-center gap-2 rounded-full border border-indigoBrand px-4 py-2 font-semibold text-indigoBrand transition hover:bg-indigoBrand hover:text-white">
              <span aria-hidden>⬇️</span>
              Download
            </button>
          </div>
        </Card>
      ))}
    </div>
  );
};
