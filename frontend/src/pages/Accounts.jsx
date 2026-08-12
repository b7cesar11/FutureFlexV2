import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Wallet } from "lucide-react";
import { apiError, brl, http } from "@/lib/api";
import { EmptyState, Metric, PageHeader, Skeleton } from "@/components/ui-kit/Primitives";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#ccff00]";

export default function Accounts() {
  const [form, setForm] = useState({ name: "", type: "checking", opening_balance: "" });
  const [showForm, setShowForm] = useState(false);
  const queryClient = useQueryClient();

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await http.get("/accounts")).data,
  });
  const { data: free } = useQuery({
    queryKey: ["free-money"],
    queryFn: async () => (await http.get("/free-money")).data,
  });

  const create = useMutation({
    mutationFn: async () =>
      http.post("/accounts", {
        name: form.name,
        type: form.type,
        opening_balance: Number(form.opening_balance || 0),
      }),
    onSuccess: () => {
      toast.success("Conta criada");
      queryClient.invalidateQueries();
      setForm({ name: "", type: "checking", opening_balance: "" });
      setShowForm(false);
    },
    onError: (e) => toast.error(apiError(e)),
  });

  return (
    <div data-testid="accounts-page">
      <PageHeader
        subtitle="Contas e saldo"
        title="Suas contas"
        right={
          <button
            data-testid="new-account-btn"
            onClick={() => setShowForm((s) => !s)}
            className="flex items-center gap-1.5 rounded-md bg-[#ccff00] px-3.5 py-2 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
          >
            <Plus size={15} /> Nova conta
          </button>
        }
      />

      {free && (
        <div className="mb-5 grid gap-4 sm:grid-cols-3">
          <Metric label="Saldo total" value={brl(free.balance)} testid="accounts-balance" />
          <Metric
            label="Pendente do mês"
            value={brl(free.pending_commitments)}
            tone="expense"
            testid="accounts-pending"
          />
          <Metric label="Livre agora" value={brl(free.free_now)} tone="free" testid="accounts-free" />
        </div>
      )}

      {showForm && (
        <div className="surface mb-5 grid gap-3 rounded-lg p-5 sm:grid-cols-4" data-testid="account-form">
          <input
            className={field}
            placeholder="Nome (ex.: Itaú)"
            data-testid="account-name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <select
            className={field}
            data-testid="account-type"
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value })}
          >
            <option value="checking">Conta corrente</option>
            <option value="savings">Poupança</option>
            <option value="cash">Dinheiro</option>
            <option value="wallet">Carteira digital</option>
          </select>
          <input
            className={`${field} num`}
            placeholder="Saldo inicial"
            data-testid="account-balance"
            value={form.opening_balance}
            onChange={(e) => setForm({ ...form, opening_balance: e.target.value })}
          />
          <button
            data-testid="account-save"
            onClick={() => create.mutate()}
            className="rounded-md bg-[#ccff00] py-2.5 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
          >
            Salvar
          </button>
        </div>
      )}

      {isLoading ? (
        <Skeleton className="h-24" />
      ) : accounts.length === 0 ? (
        <EmptyState
          title="Nenhuma conta cadastrada"
          description="O saldo das contas é a base do cálculo de dinheiro livre."
          testid="accounts-empty"
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 stagger">
          {accounts.map((account) => (
            <div
              key={account.id}
              className="surface rounded-lg p-5"
              data-testid={`account-${account.id}`}
            >
              <p className="flex items-center gap-2 text-sm text-zinc-300">
                <Wallet size={15} style={{ color: account.color }} /> {account.name}
              </p>
              <p className="num mt-2 text-2xl font-semibold text-zinc-50">
                {brl(account.current_balance)}
              </p>
              <p className="mt-1 text-[11px] text-zinc-500">
                Alterado apenas por transações reais.
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
