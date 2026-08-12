import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, CheckCircle2, Info } from "lucide-react";
import { brl, competenceLabel, http, shortCompetence } from "@/lib/api";
import { Metric, PageHeader, ProgressBar, Skeleton } from "@/components/ui-kit/Primitives";

const iconFor = (severity) =>
  severity === "warning" ? AlertTriangle : severity === "success" ? CheckCircle2 : Info;

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => (await http.get("/dashboard")).data,
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

      <div className="surface mt-4 rounded-lg p-5">
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

        <div className="space-y-4">
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
    </div>
  );
}
