import { useMemo, useState } from 'react';
import { Card } from '../components/Card';
import { approvals as approvalQueue } from '../data/mockData';

type ApprovalState = 'Pending' | 'Approved' | 'Rejected';

type ApprovalItem = {
  id: string;
  title: string;
  vendor: string;
  amount: string;
  submitted: string;
  status: ApprovalState;
};

export const ApprovalsSection = () => {
  const initial = useMemo<ApprovalItem[]>(
    () => approvalQueue.map((item) => ({ ...item })),
    []
  );
  const [items, setItems] = useState(initial);
  const [feedback, setFeedback] = useState<{ message: string; tone: 'approve' | 'reject' } | null>(null);

  const handleAction = (id: string, status: ApprovalState) => {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, status } : item)));
    setFeedback({
      message: status === 'Approved' ? 'Invoice approved and routed to ERP ✅' : 'Invoice rejected with feedback 📨',
      tone: status === 'Approved' ? 'approve' : 'reject'
    });
    setTimeout(() => setFeedback(null), 2600);
  };

  const pending = items.filter((item) => item.status === 'Pending');
  const completed = items.filter((item) => item.status !== 'Pending');

  return (
    <div className="space-y-6">
      {feedback && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm shadow-card transition ${
            feedback.tone === 'approve'
              ? 'border-crGreen/40 bg-crGreen/10 text-crGreen animate-approve'
              : 'border-crRed/40 bg-crRed/10 text-crRed animate-reject'
          }`}
        >
          {feedback.message}
        </div>
      )}

      <Card title="Pending approvals" eyebrow="Action needed">
        <div className="space-y-3">
          {pending.map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-3 rounded-2xl border border-slate-200/80 bg-white/70 p-4 transition hover:border-indigoBrand/60 dark:border-slate-800/80 dark:bg-slate-900/40 md:flex-row md:items-center md:justify-between"
            >
              <div>
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{item.title}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {item.vendor} • {item.amount} • {item.submitted}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleAction(item.id, 'Approved')}
                  className="inline-flex items-center gap-2 rounded-full bg-indigoBrand px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:shadow"
                >
                  <span aria-hidden>✓</span> Approve
                </button>
                <button
                  onClick={() => handleAction(item.id, 'Rejected')}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-500 transition hover:border-crRed hover:text-crRed"
                >
                  <span aria-hidden>✕</span> Reject
                </button>
              </div>
            </div>
          ))}
          {pending.length === 0 && (
            <div className="rounded-xl border border-slate-200/70 bg-white/40 p-6 text-sm text-slate-500 dark:border-slate-800/60 dark:bg-slate-900/30">
              Nothing left to review — enjoy your cafecito ☕️
            </div>
          )}
        </div>
      </Card>

      <Card title="History" eyebrow="Recent decisions">
        <div className="space-y-3 text-sm">
          {completed.map((item) => (
            <div
              key={item.id}
              className={`flex items-center justify-between rounded-xl border px-4 py-3 ${
                item.status === 'Approved'
                  ? 'border-crGreen/40 bg-crGreen/5 text-crGreen'
                  : 'border-crRed/40 bg-crRed/5 text-crRed'
              }`}
            >
              <div>
                <p className="font-semibold">{item.title}</p>
                <p className="text-xs opacity-80">
                  {item.vendor} • {item.amount}
                </p>
              </div>
              <span className="text-xs font-bold uppercase tracking-wide">{item.status}</span>
            </div>
          ))}
          {completed.length === 0 && (
            <p className="text-xs text-slate-400">No decisions yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
};
