import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertTriangle, ArrowUpRight, CalendarClock, CheckCircle2, CreditCard, HeartPulse, Info, Repeat,
} from "lucide-react";
import { brl, competenceLabel, formatDate, http, shortCompetence, STATUS_META } from "@/lib/api";
import {
  Metric, PageHeader, ProgressBar, Skeleton, StatusBadge,
} from "@/components/ui-kit/Primitives";

const iconFor = (severity) =>
  severity === "warning" ? AlertTriangle : severity === "success" ? CheckCircle2 : Info;

const HEALTH_BAND_COLOR = {
  excelente: "text-emerald-400",
  boa: "text-[#ccff00]",
  atencao: "text-amber-400",
  critica: "text-rose-400",
  sem_dados: "text-zinc-500",
};

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => (await http.get("/overview")).data,
  });

  if (isLoading || !data) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );
  }

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        subtitle={competenceLabel(data.competence)}
        title="Sua situação hoje"
        right={
          <Link
            to="/compromissos"
            data-testid="dashboard-to-commitments"
            className="flex items-center gap-1.5 rounded-md border border-white/10 px-3.5 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-800"
          >
            Compromissos do mês <ArrowUpRight size={14} />
          </Link>
        }
      />

      <div className="surface mb-4 rounded-lg p-6" data-testid="free-money-card">
        <p className="label-caps">Livre para gastar agora</p>
        <p
          className="num mt-2 text-4xl sm:text-5xl font-semibold text-[#ccff00]"
          data-testid="free-now-value"
        >
          {brl(data.free_now)}
        </p>
        <p className="mt-2 text-sm text-zinc-500">
          Saldo de {brl(data.balance)} menos {brl(data.pending)} de compromissos pendentes do mês.
          Com as receitas ainda previstas: <span className="num text-zinc-300">{brl(data.free_optimistic)}</span>
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 stagger">
        <Metric label="Saldo atual" value={brl(data.balance)} testid="metric-balance" />
        <Metric
          label="Vai entrar"
          value={brl(data.income_expected)}
          tone="income"
          testid="metric-income"
        />
        <Metric
          label="Comprometido"
          value={brl(data.committed)}
          tone="expense"
          hint={`${data.commitment_ratio_pct}% da renda prevista`}
          testid="metric-committed"
        />
        <Metric
          label="Pendente"
          value={brl(data.pending)}
          tone="muted"
          hint={`${data.progress_pct}% do mês já quitado`}
          testid="metric-pending"
        />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 stagger">
        <Metric
          label="Pago"
          value={brl(data.paid)}
          tone="income"
          hint="Nesta competência"
          testid="metric-paid"
        />
        <Metric
          label="Atrasado"
          value={brl(data.overdue)}
          tone={data.overdue > 0 ? "expense" : "muted"}
          hint={data.overdue > 0 ? "Compromissos vencidos e não pagos" : "Nenhum compromisso atrasado"}
          testid="metric-overdue"
        />
        <div className="surface rounded-lg p-4 sm:p-5" data-testid="dashboard-progress-card">
          <div className="flex items-end justify-between">
            <p className="label-caps">Progresso do mês</p>
            <p className="num text-sm text-zinc-300" data-testid="dashboard-progress-pct">
              {data.progress_pct}% quitado
            </p>
          </div>
          <div className="mt-3">
            <ProgressBar pct={data.progress_pct} testid="dashboard-progress" />
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3 stagger">
        <div className="surface rounded-lg p-5" data-testid="next-invoice-card">
          <div className="mb-3 flex items-center justify-between">
            <p className="label-caps flex items-center gap-2">
              <CreditCard size={14} className="text-zinc-500" /> Próxima fatura
            </p>
            <Link
              to="/cartoes"
              data-testid="dashboard-to-cards"
              className="text-zinc-500 transition-colors hover:text-zinc-200"
            >
              <ArrowUpRight size={15} />
            </Link>
          </div>
          {data.next_invoice ? (
            <div data-testid="next-invoice-content">
              <p className="num text-2xl font-semibold text-zinc-50">
                {brl(data.next_invoice.total - data.next_invoice.paid_amount)}
              </p>
              <p className="mt-1 text-sm text-zinc-400">
                {data.next_invoice.card} · {competenceLabel(data.next_invoice.competence)}
              </p>
              <p className="num mt-1 text-xs text-zinc-500">
                vence {formatDate(data.next_invoice.due_date)}
              </p>
            </div>
          ) : (
            <p className="py-4 text-sm text-zinc-500" data-testid="next-invoice-empty">
              Nenhuma fatura em aberto.
            </p>
          )}
        </div>

        <Link
          to="/assinaturas"
          data-testid="dashboard-subscriptions-card"
          className="surface rounded-lg p-5 transition-colors hover:border-white/20"
        >
          <div className="mb-3 flex items-center justify-between">
            <p className="label-caps flex items-center gap-2">
              <Repeat size={14} className="text-zinc-500" /> Assinaturas
            </p>
            <ArrowUpRight size={15} className="text-zinc-500" />
          </div>
          <p className="num text-2xl font-semibold text-zinc-50">
            {brl(data.subscriptions.monthly_total)}
            <span className="text-sm text-zinc-500">/mês</span>
          </p>
          <p className="mt-1 text-sm text-zinc-400">
            {data.subscriptions.active_count} ativas · {brl(data.subscriptions.annual_total)}/ano
          </p>
          {data.subscriptions.next_charge && (
            <p className="num mt-1 text-xs text-zinc-500">
              próxima: {data.subscriptions.next_charge.name}{" "}
              {formatDate(data.subscriptions.next_charge.date)}
            </p>
          )}
        </Link>

        <Link
          to="/saude"
          data-testid="dashboard-health-card"
          className="surface rounded-lg p-5 transition-colors hover:border-white/20"
        >
          <div className="mb-3 flex items-center justify-between">
            <p className="label-caps flex items-center gap-2">
              <HeartPulse size={14} className="text-zinc-500" /> Saúde financeira
            </p>
            <ArrowUpRight size={15} className="text-zinc-500" />
          </div>
          <p className="flex items-baseline gap-1.5">
            <span
              className={`num text-3xl font-semibold ${HEALTH_BAND_COLOR[data.health.band] || "text-zinc-50"}`}
              data-testid="dashboard-health-score"
            >
              {data.health.score}
            </span>
            <span className="num text-sm text-zinc-600">/100</span>
          </p>
          <p className={`mt-1 text-sm ${HEALTH_BAND_COLOR[data.health.band] || "text-zinc-400"}`}>
            {data.health.band_label}
          </p>
          {!data.health.has_enough_data && (
            <p className="mt-1 text-xs text-zinc-500">
              completude dos dados {data.health.data_completeness_pct}%
            </p>
          )}
        </Link>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="surface rounded-lg p-5 lg:col-span-2" data-testid="next-commitments-card">
          <div className="mb-4 flex items-center justify-between">
            <p className="label-caps flex items-center gap-2">
              <CalendarClock size={14} className="text-zinc-500" /> Próximos compromissos
            </p>
            <Link
              to="/compromissos"
              data-testid="next-commitments-link"
              className="flex items-center gap-1 text-xs text-zinc-400 transition-colors hover:text-zinc-100"
            >
              ver todos <ArrowUpRight size={13} />
            </Link>
          </div>
          {data.next_commitments.length === 0 ? (
            <p className="py-4 text-sm text-zinc-500" data-testid="next-commitments-empty">
              Nenhum compromisso em aberto neste mês.
            </p>
          ) : (
            <div className="space-y-2.5">
              {data.next_commitments.map((c) => {
                const meta = STATUS_META[c.status] || STATUS_META.future;
                return (
                  <div
                    key={c.id}
                    data-testid={`next-commitment-${c.id}`}
                    className="flex items-center justify-between gap-3 border-b border-white/[0.06] pb-2.5 last:border-0 last:pb-0"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm text-zinc-100">{c.label}</p>
                      <p className="num text-[11px] text-zinc-500">vence {formatDate(c.due_date)}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge status={c.status} meta={meta} />
                      <span className="num text-sm text-zinc-100">{brl(c.amount)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="surface rounded-lg p-5" data-testid="accounts-card">
          <p className="label-caps mb-3">Contas</p>
          {data.accounts.length === 0 && (
            <p className="text-sm text-zinc-500">Nenhuma conta cadastrada.</p>
          )}
          <div className="space-y-2.5">
            {data.accounts.map((a) => (
              <div key={a.id} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-zinc-300">
                  <span className="h-2 w-2 rounded-full" style={{ background: a.color }} />
                  {a.name}
                </span>
                <span className="num text-zinc-100">{brl(a.balance)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="surface rounded-lg p-5 lg:col-span-2" data-testid="next-months-card">
          <p className="label-caps mb-4">Próximos meses</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
                  <th className="pb-2 font-medium">Mês</th>
                  <th className="pb-2 text-right font-medium">Receitas</th>
                  <th className="pb-2 text-right font-medium">Compromissos</th>
                  <th className="pb-2 text-right font-medium">Livre</th>
                </tr>
              </thead>
              <tbody className="num">
                {data.next_months.map((row) => (
                  <tr key={row.competence} className="border-t border-white/[0.06]">
                    <td className="py-2.5 text-zinc-300">{shortCompetence(row.competence)}</td>
                    <td className="py-2.5 text-right text-emerald-400">{brl(row.income)}</td>
                    <td className="py-2.5 text-right text-rose-400">{brl(row.commitments)}</td>
                    <td className="py-2.5 text-right text-zinc-100">{brl(row.free)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="surface rounded-lg p-5" data-testid="alerts-card">
          <p className="label-caps mb-3">Merece atenção</p>
          {data.insights.length === 0 && (
            <p className="text-sm text-zinc-500">Nada crítico no momento.</p>
          )}
          <div className="space-y-3">
            {data.insights.map((insight, i) => {
              const Icon = iconFor(insight.severity);
              return (
                <div key={i} className="flex gap-2.5 text-sm text-zinc-300">
                  <Icon
                    size={15}
                    className={
                      insight.severity === "warning"
                        ? "mt-0.5 shrink-0 text-amber-400"
                        : insight.severity === "success"
                          ? "mt-0.5 shrink-0 text-emerald-400"
                          : "mt-0.5 shrink-0 text-zinc-500"
                    }
                  />
                  <span>{insight.text}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
