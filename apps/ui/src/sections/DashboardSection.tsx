import { kpiCards, cashFlowSeries } from '../data/mockData';
import { Card } from '../components/Card';

const buildSparkPath = (values: number[], width: number, height: number) => {
  if (values.length === 0) {
    return '';
  }
  const max = Math.max(...values);
  const min = Math.min(...values);
  const stepX = width / (values.length - 1 || 1);
  return values
    .map((value, index) => {
      const normalized = max === min ? 0.5 : (value - min) / (max - min);
      const x = index * stepX;
      const y = height - normalized * height;
      return `${index === 0 ? 'M' : 'L'}${x},${y}`;
    })
    .join(' ');
};

export const DashboardSection = () => {
  const values = cashFlowSeries.map((point) => point.value);
  const path = buildSparkPath(values, 220, 80);

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpiCards.map((card) => (
          <Card key={card.label} className="relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-indigoBrand/5 via-transparent to-crBlue/5" aria-hidden></div>
            <div className="relative flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {card.label}
              </p>
              <span className="text-2xl font-semibold text-slate-900 dark:text-white">{card.value}</span>
              <span
                className={`text-xs font-medium ${
                  card.trend === 'up'
                    ? 'text-crGreen'
                    : card.trend === 'down'
                    ? 'text-crRed'
                    : 'text-slate-500'
                }`}
              >
                {card.delta}
              </span>
            </div>
          </Card>
        ))}
      </div>

      <Card title="Cash Flow Trend" eyebrow="This week" className="overflow-hidden">
        <div className="grid gap-6 lg:grid-cols-[220px,1fr]">
          <div>
            <svg viewBox="0 0 220 80" className="h-24 w-full text-indigoBrand" aria-hidden>
              <path d={path} fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              {cashFlowSeries.map((point, index) => {
                const max = Math.max(...values);
                const min = Math.min(...values);
                const stepX = 220 / (values.length - 1 || 1);
                const normalized = max === min ? 0.5 : (point.value - min) / (max - min);
                const x = index * stepX;
                const y = 80 - normalized * 80;
                return <circle key={point.day} cx={x} cy={y} r={3} className="fill-indigoBrand" />;
              })}
            </svg>
            <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
              {cashFlowSeries.map((point) => (
                <span key={point.day}>{point.day}</span>
              ))}
            </div>
          </div>
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200/70 bg-white/40 p-4 text-sm dark:border-slate-800/70 dark:bg-slate-900/40">
              <p className="font-semibold text-slate-700 dark:text-slate-200">Today</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">₡13.6M collected</p>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Collections are trending 8% above average with fewer late payments from strategic vendors.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200/70 p-4 dark:border-slate-800/70">
                <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Fast track queue</p>
                <p className="mt-1 text-xl font-semibold text-slate-900 dark:text-white">14 invoices</p>
              </div>
              <div className="rounded-xl border border-slate-200/70 p-4 dark:border-slate-800/70">
                <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Avg approval time</p>
                <p className="mt-1 text-xl font-semibold text-slate-900 dark:text-white">5h 12m</p>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
