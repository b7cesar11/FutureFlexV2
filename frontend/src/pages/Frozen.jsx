import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Play, Snowflake } from "lucide-react";
import { apiError, brl, http } from "@/lib/api";
import { EmptyState, Metric, PageHeader, Skeleton } from "@/components/ui-kit/Primitives";

const TYPE_LABEL = {
  purchase_installment: "Compra parcelada",
  fixed_expense: "Despesa fixa",
  subscription: "Assinatura",
  loan: "Empréstimo",
  financing: "Financiamento",
  third_party_payable: "Terceiro a pagar",
  third_party_receivable: "Terceiro a receber",
  recurring_income: "Receita recorrente",
  other: "Outro",
};

export default function Frozen() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["frozen"],
    queryFn: async () => (await http.get("/frozen")).data,
  });

  const reactivate = useMutation({
    mutationFn: async (item) =>
      item.is_subscription
        ? http.post(`/subscriptions/${item.subscription_id}/status`, { status: "active" })
        : http.post(`/commitments/${item.commitment_id}/unfreeze`),
    onSuccess: () => {
      toast.success("Compromisso reativado — projeções e dinheiro livre atualizados");
      queryClient.invalidateQueries();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  return (
    <div data-testid="frozen-page">
      <PageHeader subtitle="Fora dos compromissos ativos" title="Congelados" />

      {isLoading || !data ? (
        <Skeleton className="h-28" />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3 stagger">
            <Metric label="Compromissos congelados" value={data.summary.count} testid="frozen-count" />
            <Metric
              label="Margem liberada por mês"
              value={brl(data.summary.monthly_released)}
              tone="free"
              testid="frozen-monthly"
            />
            <Metric
              label="Total congelado (futuro)"
              value={brl(data.summary.total_released)}
              tone="muted"
              testid="frozen-total"
            />
          </div>

          <p className="mt-4 text-sm text-zinc-500">
            Itens congelados não entram no total ativo de Compromissos do Mês, mas todo o histórico
            é preservado.
          </p>

          <div className="mt-6">
            {data.items.length === 0 ? (
              <EmptyState
                title="Nenhum compromisso congelado"
                description="Congele um compromisso pelo detalhe dele para retirá-lo temporariamente dos seus totais sem perder o histórico."
                testid="frozen-empty"
              />
            ) : (
              <div className="space-y-2.5 stagger">
                {data.items.map((item) => (
                  <div
                    key={item.commitment_id}
                    className="surface flex flex-wrap items-center gap-4 rounded-lg px-5 py-4"
                    data-testid={`frozen-${item.commitment_id}`}
                  >
                    <span className="flex h-9 w-9 items-center justify-center rounded-md bg-slate-400/10 text-slate-300">
                      <Snowflake size={16} />
                    </span>
                    <div className="flex-1 min-w-[180px]">
                      <p className="text-sm font-medium text-zinc-100">
                        {item.name}
                        {item.is_subscription && (
                          <span className="ml-2 rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                            assinatura
                          </span>
                        )}
                      </p>
                      <p className="num mt-1 text-[11px] text-zinc-500">
                        {TYPE_LABEL[item.type] || item.type} · {item.payment_source}
                        {item.person && ` · ${item.person}`}
                        {item.frozen_at &&
                          ` · congelado em ${new Date(item.frozen_at).toLocaleDateString("pt-BR")}`}
                      </p>
                      {item.reason && (
                        <p className="mt-1 text-[11px] text-zinc-400">Motivo: {item.reason}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="num text-sm text-zinc-100">{brl(item.monthly_impact)}/mês</p>
                      <p className="num text-[11px] text-zinc-500">
                        {item.future_occurrences} ocorrências futuras ·{" "}
                        {brl(item.released_total)} liberados
                      </p>
                      {item.history_preserved > 0 && (
                        <p className="num text-[11px] text-zinc-600">
                          {item.history_preserved} pagamentos no histórico
                        </p>
                      )}
                    </div>
                    <button
                      data-testid={`reactivate-${item.commitment_id}`}
                      onClick={() => reactivate.mutate(item)}
                      disabled={reactivate.isPending}
                      className="flex items-center gap-1.5 rounded-md border border-[#ccff00]/40 px-3 py-2 text-xs font-medium text-[#ccff00] transition-colors hover:bg-[#ccff00]/10 disabled:opacity-50"
                    >
                      <Play size={13} /> Reativar
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
