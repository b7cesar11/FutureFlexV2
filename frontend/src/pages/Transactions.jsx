import { useQuery } from "@tanstack/react-query";
import { ArrowDownLeft, ArrowUpRight, ArrowLeftRight } from "lucide-react";
import { brl, http } from "@/lib/api";
import { EmptyState, PageHeader, Skeleton } from "@/components/ui-kit/Primitives";

const TYPE_META = {
  expense: { label: "Gasto", icon: ArrowUpRight, color: "text-rose-400" },
  commitment_payment: { label: "Pagamento", icon: ArrowUpRight, color: "text-rose-400" },
  invoice_payment: { label: "Fatura paga", icon: ArrowUpRight, color: "text-rose-400" },
  income: { label: "Recebimento", icon: ArrowDownLeft, color: "text-emerald-400" },
  transfer: { label: "Transferência", icon: ArrowLeftRight, color: "text-zinc-300" },
};

export default function Transactions() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => (await http.get("/transactions")).data,
  });
  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await http.get("/accounts")).data,
  });

  const accountName = (id) => accounts.find((a) => a.id === id)?.name || "—";

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
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
