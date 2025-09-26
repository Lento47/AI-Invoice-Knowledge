import { useMemo, useState } from 'react';
import { Card } from '../components/Card';
import { useApprovalsQueue } from '../hooks/useWorkspaceData';
import { normaliseErrorDetail } from '../lib/api';

type Feedback = { message: string; tone: 'approve' | 'reject' };

export const ApprovalsSection = () => {
  const { data, status, error, refresh, updateStatus } = useApprovalsQueue();
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  const items = data ?? [];
  const pending = useMemo(() => items.filter((item) => item.status === 'Pending'), [items]);
  const completed = useMemo(() => items.filter((item) => item.status !== 'Pending'), [items]);
  const isLoading = status === 'loading' && items.length === 0;

  const handleAction = async (id: string, nextStatus: 'Approved' | 'Rejected') => {
    setMutationError(null);
    setPendingAction(id);
    try {
      await updateStatus(id, nextStatus);
      setFeedback({
        message:
          nextStatus === 'Approved'
            ? 'Invoice approved and routed to ERP ✅'
            : 'Invoice rejected with feedback 📨',
        tone: nextStatus === 'Approved' ? 'approve' : 'reject'
      });
      setTimeout(() => setFeedback(null), 2600);
    } catch (cause) {
      const message =
        cause instanceof Error ? normaliseErrorDetail(cause.message) : normaliseErrorDetail(cause);
      setMutationError(`Failed to update approval: ${message}`);
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <div className="space-y-6">
      {(isLoading || status === 'error') && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm ${
            status === 'error'
              ? 'border-crRed/40 bg-crRed/10 text-crRed'
              : 'border-slate-200/80 bg-white/70 text-slate-500 dark:border-slate-800/70 dark:bg-slate-900/40'
          }`}
        >
          <div className="flex items-center justify-between gap-4">
            <span>{status === 'error' ? `Unable to load approvals: ${error}` : 'Loading approvals queue…'}</span>
            {status === 'error' && (
              <button
                onClick={() => refresh()}
                className="rounded-full border border-crRed/40 px-3 py-1 text-xs font-semibold text-crRed transition hover:bg-crRed/10"
              >
                Retry
              </button>
            )}
          </div>
        </div>
      )}

      {mutationError && (
        <div className="rounded-xl border border-crRed/40 bg-crRed/10 px-4 py-3 text-sm text-crRed">{mutationError}</div>
      )}

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

      {items.length === 0 && status === 'success' && (
        <Card>
          <div className="p-6 text-center text-sm text-slate-500 dark:text-slate-400">
            All approvals are clear — enjoy your cafecito ☕️
          </div>
        </Card>
      )}

      {items.length > 0 && (
        <>
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
                      disabled={pendingAction === item.id}
                      className="inline-flex items-center gap-2 rounded-full bg-indigoBrand px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:shadow disabled:opacity-60"
                    >
                      <span aria-hidden>✓</span> Approve
                    </button>
                    <button
                      onClick={() => handleAction(item.id, 'Rejected')}
                      disabled={pendingAction === item.id}
                      className="inline-flex items-center gap-2 rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-500 transition hover:border-crRed hover:text-crRed disabled:opacity-60"
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
              {completed.length === 0 && <p className="text-xs text-slate-400">No decisions yet.</p>}
            </div>
          </Card>
        </>
      )}
    </div>
  );
};
