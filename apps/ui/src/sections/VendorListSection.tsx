import { useMemo, useState } from 'react';
import { Card } from '../components/Card';
import { vendors } from '../data/mockData';

export const VendorListSection = () => {
  const [query, setQuery] = useState('');
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return vendors;
    }
    return vendors.filter((vendor) =>
      [vendor.name, vendor.category, vendor.contact, vendor.status].some((field) =>
        field.toLowerCase().includes(normalized)
      )
    );
  }, [query]);

  return (
    <Card title="Vendor directory" eyebrow="Suppliers">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:w-72">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search vendors…"
            className="w-full rounded-full border border-slate-300 bg-white/80 px-4 py-2 text-sm text-slate-600 placeholder:text-slate-400 shadow-sm transition focus:border-indigoBrand focus:outline-none focus:ring-2 focus:ring-indigoBrand/20 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200"
          />
          <span className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-slate-400">⌕</span>
        </div>
        <p className="text-xs text-slate-400 dark:text-slate-500">
          Showing <span className="font-semibold text-indigoBrand">{filtered.length}</span> of {vendors.length} vendors
        </p>
      </div>
      <div className="overflow-hidden rounded-xl border border-slate-200/70 dark:border-slate-800/70">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
          <thead className="bg-slate-50/70 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/40 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">Vendor</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Contact</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
            {filtered.map((vendor, index) => (
              <tr
                key={vendor.id}
                className={index % 2 === 0 ? 'bg-white/70 dark:bg-slate-900/40' : 'bg-slate-50/40 dark:bg-slate-900/30'}
              >
                <td className="px-4 py-3 font-medium text-slate-700 dark:text-slate-200">{vendor.name}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{vendor.category}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{vendor.contact}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center rounded-full bg-indigoBrand/10 px-3 py-1 text-xs font-semibold text-indigoBrand">
                    {vendor.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="p-6 text-center text-sm text-slate-500 dark:text-slate-400">No vendors match your search.</div>
        )}
      </div>
    </Card>
  );
};
