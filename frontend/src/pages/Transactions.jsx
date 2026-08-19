import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowDownLeft, ArrowUpRight, ArrowLeftRight, Trash2, X } from "lucide-react";
import { apiError, brl, http } from "@/lib/api";
import { EmptyState, PageHeader, Skeleton } from "@/components/ui-kit/Primitives";

const TYPE_META = {
  expense: { label: "Gasto", icon: ArrowUpRight, color: "text-rose-400" },
  commitment_payment: { label: "Pagamento", icon: ArrowUpRight, color: "text-rose-400" },
  invoice_payment: { label: "Fatura paga", icon: ArrowUpRight, color: "text-rose-400" },
  income: { label: "Recebimento", icon: ArrowDownLeft, color: "text-emerald-400" },
  transfer: { label: "Transferência", icon: ArrowLeftRight, color: "text-zinc-300" },
};

export default function Transactions() {
  const [deleteTarget, setDeleteTarget] = useState(null);
  const queryClient = useQueryClient();

  const { data = [], isLoading } = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => (await http.get("/transactions")).data,
  });
  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await http.get("/accounts")).data,
  });

  const deleteMutation = useMutation({
    mutationFn: async (id) => http.delete(`/transactions/${id}`),
    onSuccess: () => {
      toast.success("Lançamento excluído e saldo estornado");
      queryClient.invalidateQueries();
      setDeleteTarget(null);
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const accountName = (id) => accounts.find((a) => a.id === id)?.name || "—";
  const canDelete = (tx) =>
    ["expense", "income", "transfer"].includes(tx.type) &&
    tx.source === "manual" &&
    !tx.occurrence_id &&
    !tx.invoice_id;

  return (
    <div data-testid="transactions-page">
      <PageHeader subtitle="Histórico real" title="Transações" />
      <p className="mb-5 text-sm text-zinc-500">
        Aqui só aparece o que <span className="text-zinc-200">realmente aconteceu</span>. Previsões
        ficam em Compromissos do Mês.
      </p>

      {isLoading ? (
        <Skeleton className="h-24" />
      ) : data.length === 0 ? (
        <EmptyState
          title="Nenhuma transação registrada"
          description="Compras no cartão não geram transação: apenas o pagamento da fatura movimenta a conta."
          testid="transactions-empty"
        />
      ) : (
        <div className="space-y-2 stagger">
          {data.map((tx) => {
            const meta = TYPE_META[tx.type] || TYPE_META.expense;
            const Icon = meta.icon;
            return (
              <div
                key={tx.id}
                className="realizado flex flex-wrap items-center gap-4 rounded-lg px-5 py-3.5"
                data-testid={`transaction-${tx.id}`}
              >
                <span className={`flex h-8 w-8 items-center justify-center rounded-md bg-zinc-800 ${meta.color}`}>
                  <Icon size={15} />
                </span>
                <div className="flex-1 min-w-[160px]">
                  <p className="text-sm text-zinc-100">{tx.description || meta.label}</p>
                  <p className="num mt-0.5 text-[11px] text-zinc-500">
                    {new Date(tx.date).toLocaleDateString("pt-BR")} · {meta.label} ·{" "}
                    {accountName(tx.account_id)}
                  </p>
                </div>
                <span className={`num text-sm ${tx.type === "income" ? "text-emerald-400" : "text-zinc-100"}`}>
                  {tx.type === "income" ? "+" : "−"}
                  {brl(tx.amount)}
                </span>
                {canDelete(tx) && (
                  <button
                    data-testid={`transaction-delete-${tx.id}`}
                    onClick={() => setDeleteTarget(tx)}
                    title="Excluir lançamento feito por engano"
                    className="rounded-md border border-rose-500/30 p-2 text-rose-400 transition-colors hover:bg-rose-500/10"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setDeleteTarget(null)} />
          <div
            className="relative z-10 w-full sm:max-w-md rounded-t-2xl sm:rounded-xl border border-white/10 bg-[#0d0d0f] p-6"
            data-testid="transaction-delete-dialog"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="label-caps text-rose-400">Excluir lançamento</p>
                <h3 className="mt-1 text-lg font-semibold">{deleteTarget.description || "Lançamento manual"}</h3>
                <p className="num mt-1 text-sm text-zinc-400">{brl(deleteTarget.amount)}</p>
              </div>
              <button onClick={() => setDeleteTarget(null)} className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800">
                <X size={18} />
              </button>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-zinc-400">
              O lançamento será removido e o efeito dele no saldo será estornado. Pagamentos de compromissos e
              faturas não podem ser apagados por esta opção.
            </p>
            <div className="mt-5 flex gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="flex-1 rounded-md border border-zinc-800 py-3 text-sm text-zinc-300 hover:bg-zinc-800"
              >
                Cancelar
              </button>
              <button
                data-testid="transaction-delete-confirm"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
                className="flex-1 rounded-md bg-rose-500 py-3 text-sm font-semibold text-white disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Excluindo..." : "Excluir e estornar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
