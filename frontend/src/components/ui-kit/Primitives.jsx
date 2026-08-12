export const Metric = ({ label, value, hint, tone = "default", testid, big = false }) => {
  const tones = {
    default: "text-zinc-50",
    income: "text-emerald-400",
    expense: "text-rose-400",
    free: "text-[#ccff00]",
    muted: "text-zinc-400",
  };
  return (
    <div className="surface rounded-lg p-4 sm:p-5" data-testid={testid}>
      <p className="label-caps">{label}</p>
      <p
        className={`num mt-2 ${big ? "text-2xl sm:text-3xl" : "text-xl sm:text-2xl"} font-semibold ${tones[tone]}`}
        data-testid={testid ? `${testid}-value` : undefined}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-zinc-500">{hint}</p>}
    </div>
  );
};

export const ProgressBar = ({ pct, testid }) => (
  <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800" data-testid={testid}>
    <div
      className="h-full rounded-full bg-[#ccff00] transition-[width] duration-500"
      style={{ width: `${Math.min(Math.max(pct || 0, 0), 100)}%` }}
    />
  </div>
);

export const StatusBadge = ({ status, meta }) => (
  <span
    className={`num rounded border px-1.5 py-0.5 text-[10px] ${meta.className}`}
    data-testid={`status-${status}`}
  >
    {meta.label}
  </span>
);

export const EmptyState = ({ title, description, action, testid }) => (
  <div
    className="rounded-lg border border-dashed border-white/12 px-6 py-14 text-center"
    data-testid={testid}
  >
    <p className="num text-3xl text-zinc-700">—</p>
    <p className="mt-3 text-base font-medium text-zinc-200">{title}</p>
    {description && <p className="mx-auto mt-1 max-w-sm text-sm text-zinc-500">{description}</p>}
    {action && <div className="mt-6 flex justify-center">{action}</div>}
  </div>
);

export const Skeleton = ({ className = "" }) => (
  <div className={`animate-pulse rounded-md bg-zinc-800/70 ${className}`} />
);

export const PageHeader = ({ title, subtitle, right }) => (
  <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
    <div>
      <p className="label-caps">{subtitle}</p>
      <h2 className="mt-1 text-2xl sm:text-3xl font-semibold tracking-tight text-zinc-50">
        {title}
      </h2>
    </div>
    {right}
  </div>
);
