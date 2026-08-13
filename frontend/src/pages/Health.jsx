import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, HelpCircle, TriangleAlert } from "lucide-react";
import { brl, http } from "@/lib/api";
import { PageHeader, ProgressBar, Skeleton } from "@/components/ui-kit/Primitives";

const VERDICT = {
  bom: { icon: CheckCircle2, color: "text-emerald-400", bar: "bg-emerald-400", label: "Bom" },
  atencao: { icon: TriangleAlert, color: "text-amber-400", bar: "bg-amber-400", label: "Atenção" },
  critico: { icon: AlertCircle, color: "text-rose-400", bar: "bg-rose-400", label: "Crítico" },
  sem_dados: { icon: HelpCircle, color: "text-zinc-500", bar: "bg-zinc-700", label: "Sem dados" },
};

const BAND_COLOR = {
  excelente: "text-emerald-400",
  boa: "text-[#ccff00]",
  atencao: "text-amber-400",
  critica: "text-rose-400",
  sem_dados: "text-zinc-500",
};

export default function Health() {
  const { data, isLoading } = useQuery({
    queryKey: ["health-score"],
    queryFn: async () => (await http.get("/health-score")).data,
  });

  if (isLoading || !data) return <Skeleton className="h-96" />;

  return (
    <div data-testid="health-page">
      <PageHeader subtitle="Diagnóstico explicável" title="Saúde Financeira" />

      <div className="surface rounded-lg p-6 sm:p-8" data-testid="health-score-card">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="label-caps">Score geral</p>
            <p className="mt-2 flex items-baseline gap-2">
              <span
                className={`num text-5xl sm:text-6xl font-semibold ${BAND_COLOR[data.band]}`}
                data-testid="health-score-value"
              >
                {data.score}
              </span>
              <span className="num text-xl text-zinc-600">/100</span>
            </p>
            <p className={`mt-1 text-sm ${BAND_COLOR[data.band]}`} data-testid="health-band">
              {data.band_label}
            </p>
          </div>
          <div className="min-w-[220px] flex-1">
            <ProgressBar pct={data.score} testid="health-progress" />
            <p className="num mt-2 text-[11px] text-zinc-500">
              {data.earned_points} de {data.available_weight} pontos avaliáveis · completude dos
              dados {data.data_completeness_pct}%
            </p>
          </div>
        </div>

        {!data.has_enough_data && (
          <div
            className="mt-5 rounded-md border border-amber-400/30 bg-amber-400/5 px-4 py-3 text-sm text-amber-200"
            data-testid="health-insufficient-data"
          >
            Ainda faltam dados para um diagnóstico confiável. Cadastre contas, receitas e
            compromissos para que todos os fatores sejam avaliados.
          </div>
        )}
      </div>

      {data.top_actions.length > 0 && (
        <div className="surface mt-4 rounded-lg p-5" data-testid="health-top-actions">
          <p className="label-caps mb-3">O que mais derruba seu score</p>
          <div className="space-y-2.5">
            {data.top_actions.map((action) => (
              <div key={action.factor} className="flex gap-3 text-sm">
                <span className="num shrink-0 rounded bg-rose-400/10 px-1.5 py-0.5 text-[11px] text-rose-400">
                  −{action.lost_points}
                </span>
                <span className="text-zinc-300">
                  <span className="text-zinc-100">{action.factor}:</span> {action.recommendation}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="label-caps mt-8 mb-3">Fatores do cálculo</p>
      <div className="grid gap-3 lg:grid-cols-2 stagger">
        {data.factors.map((factor) => {
          const meta = VERDICT[factor.verdict];
          const Icon = meta.icon;
          const pct = factor.max_points ? (factor.points / factor.max_points) * 100 : 0;
          return (
            <div
              key={factor.key}
              className="surface rounded-lg p-5"
              data-testid={`health-factor-${factor.key}`}
            >
              <div className="flex items-start justify-between gap-3">
                <p className="flex items-center gap-2 text-sm font-medium text-zinc-100">
                  <Icon size={15} className={meta.color} /> {factor.label}
                </p>
                <p className="num shrink-0 text-sm text-zinc-300">
                  {factor.points}
                  <span className="text-zinc-600">/{factor.max_points}</span>
                </p>
              </div>

              <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
                <div
                  className={`h-full rounded-full ${meta.bar} transition-[width] duration-500`}
                  style={{ width: `${pct}%` }}
                />
              </div>

              <div className="num mt-2 flex justify-between text-[10px] text-zinc-500">
                <span>peso {factor.weight} pontos</span>
                <span className={meta.color}>{meta.label}</span>
              </div>

              <p className="mt-3 text-sm leading-relaxed text-zinc-400">{factor.explanation}</p>
              <p className="mt-2 text-[11px] leading-relaxed text-zinc-500">
                <span className="text-zinc-400">Recomendação:</span> {factor.recommendation}
              </p>
            </div>
          );
        })}
      </div>

      <div className="surface mt-6 rounded-lg p-5" data-testid="health-metrics-used">
        <p className="label-caps mb-3">Base do cálculo (dados reais usados)</p>
        <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          {[
            ["Renda mensal prevista", brl(data.metrics_used.monthly_income)],
            ["Compromissos do mês", brl(data.metrics_used.committed)],
            ["Saldo em contas", brl(data.metrics_used.balance)],
            ["Dinheiro livre", brl(data.metrics_used.free_now)],
            ["Atrasado", brl(data.metrics_used.overdue)],
            ["Faturas em aberto", brl(data.metrics_used.open_invoices_total)],
            ["Dívida a pagar (futuro)", brl(data.metrics_used.debt_remaining)],
            ["Parcelas no mês", brl(data.metrics_used.installment_monthly)],
            ["Fixas + assinaturas", brl(data.metrics_used.fixed_monthly)],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between border-b border-white/[0.06] pb-2">
              <span className="text-zinc-500">{label}</span>
              <span className="num text-zinc-200">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
