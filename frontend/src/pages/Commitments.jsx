import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ChevronDown, ChevronRight, Snowflake, X } from "lucide-react";
import { apiError, brl, competenceLabel, formatDate, http, STATUS_META } from "@/lib/api";
import { useMonth } from "@/contexts/MonthContext";
import { MonthSwitcher } from "@/components/layout/MonthSwitcher";
import {
  EmptyState, Metric, PageHeader, ProgressBar, Skeleton, StatusBadge,
} from "@/components/ui-kit/Primitives";
import { CommitmentDetailDrawer } from "@/components/CommitmentDetailDrawer";
import { PayDialog } from "@/components/PayDialog";

export default function Commitments() {
  const { competence } = useMonth();
  const [openGroups, setOpenGroups] = useState({});
  const [detailId, setDetailId] = useState(null);
  const [payTarget, setPayTarget] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["month", competence],
    queryFn: async () => (await http.get(`/months/${competence}`)).data,
  });

  const toggle = (key) => setOpenGroups((g) => ({ ...g, [key]: !g[key] }));

  return (
    <div data-testid="commitments-page">
      <PageHeader
        subtitle="Compromissos do mês"
        title={<span className="capitalize">{competenceLabel(competence)}</span>}
        right={<div className="hidden md:block"><MonthSwitcher /></div>}
      />

      {isLoading || !data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5 stagger">
            <Metric
              label="Receitas previstas"
              value={brl(data.income_expected)}
              tone="income"
              testid="month-income"
            />
            <Metric
              label="Compromissos"
              value={brl(data.committed)}
              tone="expense"
              testid="month-committed"
            />
            <Metric label="Pago" value={brl(data.paid)} testid="month-paid" />
            <Metric label="Pendente" value={brl(data.pending)} tone="muted" testid="month-pending" />
            <Metric
              label="Livre projetado"
              value={brl(data.free_projected)}
              tone="free"
              testid="month-free"
            />
          </div>

          <div className="surface mt-4 rounded-lg p-5">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <p className="label-caps">Quitação do mês</p>
              <div className="num flex gap-4 text-xs text-zinc-400">
                <span data-testid="month-progress-pct">{data.progress_pct}% quitado</span>
                {data.frozen_total > 0 && (
                  <span className="text-slate-400" data-testid="month-frozen">
                    {brl(data.frozen_total)} congelado
                  </span>
                )}
                {data.overdue > 0 && (
                  <span className="text-rose-400" data-testid="month-overdue">
                    {brl(data.overdue)} atrasado
                  </span>
                )}
              </div>
            </div>
            <div className="mt-3">
              <ProgressBar pct={data.progress_pct} testid="month-progress" />
            </div>
          </div>

          {data.insights.length > 0 && (
            <div className="mt-4 space-y-2">
              {data.insights.map((insight, i) => (
                <div
                  key={i}
                  data-testid={`month-insight-${i}`}
                  className="rounded-md border border-white/[0.08] bg-zinc-900/60 px-4 py-2.5 text-sm text-zinc-300"
                >
                  {insight.text}
                </div>
              ))}
            </div>
          )}

          <div className="mt-6 space-y-3">
            {data.groups.length === 0 && (
              <EmptyState
                title="Nenhum compromisso neste mês"
                description="Use o botão Registrar para criar uma compra parcelada, despesa fixa, assinatura ou terceiro. Tudo aparece automaticamente aqui."
                testid="commitments-empty"
              />
            )}

            {data.groups.map((group) => {
              const open = openGroups[group.key] ?? true;
              return (
                <div
                  key={group.key}
                  className="surface overflow-hidden rounded-lg"
                  data-testid={`group-${group.key}`}
                >
                  <button
                    onClick={() => toggle(group.key)}
                    data-testid={`group-toggle-${group.key}`}
                    className="flex w-full items-center justify-between px-5 py-4 transition-colors hover:bg-zinc-800/40"
                  >
                    <span className="flex items-center gap-2.5">
                      {open ? (
                        <ChevronDown size={16} className="text-zinc-500" />
                      ) : (
                        <ChevronRight size={16} className="text-zinc-500" />
                      )}
                      <span className="text-sm font-medium text-zinc-100">{group.label}</span>
                      <span className="num rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                        {group.items.length}
                      </span>
                    </span>
                    <span
                      className={`num text-sm ${group.key === "income" ? "text-emerald-400" : "text-zinc-100"}`}
                      data-testid={`group-total-${group.key}`}
                    >
                      {brl(group.total)}
                    </span>
                  </button>

                  {open && (
                    <div className="border-t border-white/[0.06]">
                      {group.items.map((item) => {
                        const meta = STATUS_META[item.status] || STATUS_META.future;
                        return (
                          <div
                            key={item.id}
                            data-testid={`occurrence-${item.id}`}
                            className={`flex flex-wrap items-center gap-3 px-5 py-3.5 transition-colors hover:bg-zinc-800/30 ${
                              item.counts_in_total ? "" : "bg-zinc-950/40"
                            }`}
                          >
                            <button
                              onClick={() => item.commitment_id && setDetailId(item.commitment_id)}
                              data-testid={`occurrence-open-${item.id}`}
                              className="flex-1 min-w-[180px] text-left"
                            >
                              <p className="text-sm text-zinc-100">{item.label}</p>
                              <p className="num mt-0.5 text-[11px] text-zinc-500">
                                vence {formatDate(item.due_date)}
                                {!item.counts_in_total && " · compõe a fatura"}
                                {item.detail?.third_party_responsible && " · terceiro responsável"}
                              </p>
                            </button>
                            <StatusBadge status={item.status} meta={meta} />
                            <span
                              className={`num w-24 text-right text-sm ${
                                item.direction === "inflow" ? "text-emerald-400" : "text-zinc-100"
                              } ${item.counts_in_total ? "" : "opacity-60"}`}
                            >
                              {item.direction === "inflow" ? "+" : ""}
                              {brl(item.amount)}
                            </span>
                            {item.status !== "paid" && item.status !== "frozen" && item.counts_in_total && (
                              <button
                                data-testid={`pay-btn-${item.id}`}
                                onClick={() => setPayTarget(item)}
                                className="rounded-md border border-[#ccff00]/40 px-2.5 py-1 text-[11px] font-medium text-[#ccff00] transition-colors hover:bg-[#ccff00]/10"
                              >
                                {item.direction === "inflow" ? "Receber" : "Pagar"}
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}

      <CommitmentDetailDrawer commitmentId={detailId} onClose={() => setDetailId(null)} />
      <PayDialog target={payTarget} onClose={() => setPayTarget(null)} />
    </div>
  );
}
