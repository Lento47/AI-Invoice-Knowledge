import { Card } from '../components/Card';
import { reports } from '../data/mockData';

export const ReportsSection = () => {
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
