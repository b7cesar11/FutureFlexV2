import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Pencil } from "lucide-react";
import { brl, competenceLabel, formatDate, http, STATUS_META } from "@/lib/api";
import { useMonth } from "@/contexts/MonthContext";
import { MonthSwitcher } from "@/components/layout/MonthSwitcher";
import {
  EmptyState, Metric, PageHeader, ProgressBar, Skeleton, StatusBadge,
} from "@/components/ui-kit/Primitives";
import { CommitmentDetailDrawer } from "@/components/CommitmentDetailDrawer";
import { PayDialog } from "@/components/PayDialog";
import { EditAmountDialog } from "@/components/EditAmountDialog";

function dueDateValue(item) {
  if (!item?.due_date) return Number.POSITIVE_INFINITY;
  const parsed = new Date(item.due_date).getTime();
  return Number.isNaN(parsed) ? Number.POSITIVE_INFINITY : parsed;
}

function orderByDueDate(items) {
  return [...items].sort((a, b) => {
    const byDueDate = dueDateValue(a) - dueDateValue(b);
    if (byDueDate !== 0) return byDueDate;
    return String(a.label || "").localeCompare(String(b.label || ""), "pt-BR");
  });
}

export default function Commitments() {
  const { competence } = useMonth();
  const [openGroups, setOpenGroups] = useState({});
  const [sortByDueDate, setSortByDueDate] = useState(false);
  const [detailId, setDetailId] = useState(null);
  const [payTarget, setPayTarget] = useState(null);
  const [editTarget, setEditTarget] = useState(null);

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
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5 stagger">
            <Metric label="Receitas previstas" value={brl(data.income_expected)} tone="income" testid="month-income" />
            <Metric label="Compromissos" value={brl(data.committed)} tone="expense" testid="month-committed" />
            <Metric label="Pago" value={brl(data.paid)} testid="month-paid" />
            <Metric label="Pendente" value={brl(data.pending)} tone="muted" testid="month-pending" />
            <Metric label="Livre projetado" value={brl(data.free_projected)} tone="free" testid="month-free" />
          </div>

          <div className="surface mt-4 rounded-lg p-5">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <p className="label-caps">Quitação do mês</p>
              <div className="num flex gap-4 text-xs text-zinc-400">
                <span data-testid="month-progress-pct">{data.progress_pct}% quitado</span>
                {data.frozen_total > 0 && <span className="text-slate-400" data-testid="month-frozen">{brl(data.frozen_total)} congelado</span>}
                {data.overdue > 0 && <span className="text-rose-400" data-testid="month-overdue">{brl(data.overdue)} atrasado</span>}
              </div>
            </div>
            <div className="mt-3"><ProgressBar pct={data.progress_pct} testid="month-progress" /></div>
          </div>

          {data.insights.length > 0 && (
            <div className="mt-4 space-y-2">
              {data.insights.map((insight, i) => (
                <div key={i} data-testid={`month-insight-${i}`}
                  className="rounded-md border border-white/[0.08] bg-zinc-900/60 px-4 py-2.5 text-sm text-zinc-300">
                  {insight.text}
                </div>
              ))}
            </div>
          )}

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="label-caps">Lista do mês</p>
              <p className="mt-1 text-xs text-zinc-500">Ative a ordenação para ver primeiro os boletos e compromissos que vencem antes.</p>
            </div>
            <button
              type="button"
              data-testid="sort-by-due-date-toggle"
              aria-pressed={sortByDueDate}
              onClick={() => setSortByDueDate((current) => !current)}
              className={`rounded-md border px-3 py-2 text-xs font-medium transition-colors ${
                sortByDueDate
                  ? "border-[#ccff00]/50 bg-[#ccff00]/10 text-[#ccff00]"
                  : "border-zinc-700 bg-zinc-900/70 text-zinc-300 hover:border-zinc-600 hover:text-zinc-100"
              }`}
            >
              Ordenar por vencimento: {sortByDueDate ? "ativado" : "desativado"}
            </button>
          </div>

          <div className="mt-3 space-y-3">
            {data.groups.length === 0 && (
              <EmptyState title="Nenhum compromisso neste mês"
                description="Use o botão Registrar para criar uma compra parcelada, despesa fixa, assinatura ou terceiro. Tudo aparece automaticamente aqui."
                testid="commitments-empty" />
            )}

            {data.groups.map((group) => {
              const open = openGroups[group.key] ?? true;
              const items = sortByDueDate ? orderByDueDate(group.items) : group.items;
              return (
                <div key={group.key} className="surface overflow-hidden rounded-lg" data-testid={`group-${group.key}`}>
                  <button onClick={() => toggle(group.key)} data-testid={`group-toggle-${group.key}`}
                    className="flex w-full items-center justify-between px-5 py-4 transition-colors hover:bg-zinc-800/40">
                    <span className="flex items-center gap-2.5">
                      {open ? <ChevronDown size={16} className="text-zinc-500" /> : <ChevronRight size={16} className="text-zinc-500" />}
                      <span className="text-sm font-medium text-zinc-100">{group.label}</span>
                      <span className="num rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">{group.items.length}</span>
                    </span>
                    <span className={`num text-sm ${group.key === "income" ? "text-emerald-400" : "text-zinc-100"}`}
                      data-testid={`group-total-${group.key}`}>{brl(group.total)}</span>
                  </button>

                  {open && (
                    <div className="border-t border-white/[0.06]">
                      {items.map((item) => {
                        const meta = STATUS_META[item.status] || STATUS_META.future;
                        const isInvoiceAggregate = item.kind === "invoice";
                        return (
                          <div key={item.id} data-testid={`occurrence-${item.id}`}
                            data-due-date={item.due_date || ""}
                            className={`flex flex-wrap items-center gap-3 px-5 py-3.5 transition-colors hover:bg-zinc-800/30 ${item.counts_in_total ? "" : "bg-zinc-950/40"}`}>
                            <button onClick={() => item.commitment_id && setDetailId(item.commitment_id)}
                              data-testid={`occurrence-open-${item.id}`} className="flex-1 min-w-[180px] text-left">
                              <p className="text-sm text-zinc-100">{item.label}</p>
                              <p className="num mt-0.5 text-[11px] text-zinc-500">
                                vence {formatDate(item.due_date)}
                                {!item.counts_in_total && " · compõe a fatura"}
                                {item.detail?.third_party_responsible && " · terceiro responsável"}
                                {isInvoiceAggregate && " · total calculado pelos itens"}
                              </p>
                            </button>
                            <StatusBadge status={item.status} meta={meta} />
                            <span className={`num w-24 text-right text-sm ${item.direction === "inflow" ? "text-emerald-400" : "text-zinc-100"} ${item.counts_in_total ? "" : "opacity-60"}`}>
                              {item.direction === "inflow" ? "+" : ""}{brl(item.amount)}
                              {!isInvoiceAggregate && item.amount_source === "override" && (
                                <span data-testid={`occurrence-override-${item.id}`} title="Valor ajustado para este mês"
                                  className="ml-1.5 rounded bg-[#ccff00]/15 px-1 py-0.5 text-[9px] font-medium text-[#ccff00] align-middle">ajustado</span>
                              )}
                            </span>
                            {!isInvoiceAggregate && item.status !== "paid" && item.status !== "cancelled" && item.status !== "frozen" && (
                              <button data-testid={`edit-amount-btn-${item.id}`} onClick={() => setEditTarget(item)} title="Editar valor"
                                className="rounded-md border border-zinc-700 p-1.5 text-zinc-400 transition-colors hover:border-[#ccff00]/40 hover:text-[#ccff00]">
                                <Pencil size={13} />
                              </button>
                            )}
                            {item.status !== "paid" && item.status !== "frozen" && item.counts_in_total && (
                              <button data-testid={`pay-btn-${item.id}`} onClick={() => setPayTarget(item)}
                                className="rounded-md border border-[#ccff00]/40 px-2.5 py-1 text-[11px] font-medium text-[#ccff00] transition-colors hover:bg-[#ccff00]/10">
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
      <EditAmountDialog target={editTarget} onClose={() => setEditTarget(null)} />
    </div>
  );
}
