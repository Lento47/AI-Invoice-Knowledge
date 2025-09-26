import { Card } from '../components/Card';
import { useInvoiceData } from '../hooks/useWorkspaceData';

export const InvoiceViewerSection = () => {
  const { data, status, error, refresh } = useInvoiceData();
  const summary = data?.summary;
  const lineItems = data?.line_items ?? [];
  const isLoading = status === 'loading' && !data;

  return (
    <div className="space-y-6">
      {(isLoading || status === 'error') && (
        <Card>
          <div className="flex items-center justify-between gap-4 text-sm">
            <span className={status === 'error' ? 'text-crRed' : 'text-slate-500 dark:text-slate-400'}>
              {status === 'error' ? `Unable to load invoice: ${error}` : 'Fetching invoice details…'}
            </span>
            {status === 'error' && (
              <button
                onClick={() => refresh()}
                className="rounded-full border border-crRed/40 px-3 py-1 text-xs font-semibold text-crRed transition hover:bg-crRed/10"
              >
                Retry
              </button>
            )}
          </div>
        </Card>
      )}

      {summary && (
        <Card title="Invoice Summary" eyebrow={summary.id} actions={<InvoiceActions />}>
          <dl className="grid gap-4 sm:grid-cols-2">
            <Item label="Vendor" value={summary.vendor} />
            <Item label="Status" value={summary.status} accent="bg-amber-100 text-amber-700" />
            <Item label="Issued" value={summary.issued_on} />
            <Item label="Due" value={summary.due_on} />
            <Item label="Total" value={summary.amount} emphasis />
            <Item label="Reference" value={summary.reference} />
            <div className="sm:col-span-2">
              <Item label="Notes" value={summary.notes ?? '—'} />
            </div>
          </dl>
        </Card>
      )}

      {lineItems.length > 0 ? (
        <Card title="Line items" eyebrow="Breakdown">
          <div className="overflow-hidden rounded-xl border border-slate-200/70 dark:border-slate-800/70">
            <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
              <thead className="bg-slate-50/70 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/40 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3">Qty</th>
                  <th className="px-4 py-3">Unit Cost</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
                {lineItems.map((item, index) => (
                  <tr
                    key={item.id}
                    className={index % 2 === 0 ? 'bg-white/70 dark:bg-slate-900/40' : 'bg-slate-50/50 dark:bg-slate-900/20'}
                  >
                    <td className="px-4 py-3 font-medium text-slate-700 dark:text-slate-200">{item.description}</td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{item.quantity}</td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{item.unit_cost}</td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-700 dark:text-slate-200">{item.amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        status === 'success' && (
          <Card>
            <div className="p-6 text-center text-sm text-slate-500 dark:text-slate-400">
              No line items were returned for this invoice.
            </div>
          </Card>
        )
      )}
    </div>
  );
};

type ItemProps = {
  label: string;
  value: string;
  emphasis?: boolean;
  accent?: string;
};

const Item = ({ label, value, emphasis, accent }: ItemProps) => (
  <div>
    <dt className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</dt>
    <dd
      className={`mt-1 text-base ${
        accent ? accent : emphasis ? 'font-semibold text-slate-900 dark:text-white' : 'text-slate-700 dark:text-slate-200'
      }`}
    >
      {value}
    </dd>
  </div>
);

const InvoiceActions = () => (
  <div className="flex gap-2">
    <button className="rounded-full border border-indigoBrand px-4 py-2 text-xs font-semibold text-indigoBrand transition hover:bg-indigoBrand hover:text-white">
      Approve
    </button>
    <button className="rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-500 transition hover:border-crRed hover:text-crRed">
      Reject
    </button>
  </div>
);
