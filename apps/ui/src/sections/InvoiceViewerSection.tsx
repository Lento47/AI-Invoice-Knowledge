import { Card } from '../components/Card';
import { invoiceLineItems, invoiceSummary } from '../data/mockData';

export const InvoiceViewerSection = () => {
  return (
    <div className="space-y-6">
      <Card title="Invoice Summary" eyebrow="INV-2098" actions={<InvoiceActions />}>
        <dl className="grid gap-4 sm:grid-cols-2">
          <Item label="Vendor" value={invoiceSummary.vendor} />
          <Item label="Status" value={invoiceSummary.status} accent="bg-amber-100 text-amber-700" />
          <Item label="Issued" value={invoiceSummary.issuedOn} />
          <Item label="Due" value={invoiceSummary.dueOn} />
          <Item label="Total" value={invoiceSummary.amount} emphasis />
          <Item label="Reference" value={invoiceSummary.reference} />
          <div className="sm:col-span-2">
            <Item label="Notes" value={invoiceSummary.notes} />
          </div>
        </dl>
      </Card>

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
              {invoiceLineItems.map((item, index) => (
                <tr
                  key={item.id}
                  className={index % 2 === 0 ? 'bg-white/70 dark:bg-slate-900/40' : 'bg-slate-50/50 dark:bg-slate-900/20'}
                >
                  <td className="px-4 py-3 font-medium text-slate-700 dark:text-slate-200">{item.description}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{item.quantity}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{item.unitCost}</td>
                  <td className="px-4 py-3 text-right font-semibold text-slate-700 dark:text-slate-200">{item.amount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
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
