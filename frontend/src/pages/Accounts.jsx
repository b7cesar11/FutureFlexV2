import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Plus, Trash2, Wallet, X } from "lucide-react";
import { apiError, brl, http, parseMoneyInput } from "@/lib/api";
import { EmptyState, Metric, PageHeader, Skeleton } from "@/components/ui-kit/Primitives";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#ccff00]";
const emptyForm = { name: "", type: "checking", opening_balance: "" };

export default function Accounts() {
  const [form, setForm] = useState(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const queryClient = useQueryClient();

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await http.get("/accounts")).data,
  });
  const { data: free } = useQuery({
    queryKey: ["free-money"],
    queryFn: async () => (await http.get("/free-money")).data,
  });

  const reset = () => {
    setForm(emptyForm);
    setEditingId(null);
    setShowForm(false);
  };

  const save = useMutation({
    mutationFn: async () => {
      const name = form.name.trim();
      if (!name) throw new Error("Informe o nome da conta");
      if (editingId) {
        return http.patch(`/accounts/${editingId}`, { name, type: form.type });
      }
      const parsedBalance = form.opening_balance ? parseMoneyInput(form.opening_balance) : 0;
      if (!Number.isFinite(parsedBalance)) throw new Error("Informe um saldo inicial válido");
      return http.post("/accounts", {
        name,
        type: form.type,
        opening_balance: parsedBalance,
      });
    },
    onSuccess: () => {
      toast.success(editingId ? "Conta atualizada" : "Conta criada");
      queryClient.invalidateQueries();
      reset();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const remove = useMutation({
    mutationFn: async (id) => http.delete(`/accounts/${id}`),
    onSuccess: () => {
      toast.success("Conta excluída");
      queryClient.invalidateQueries();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const startEdit = (account) => {
    setEditingId(account.id);
    setForm({ name: account.name || "", type: account.type || "checking", opening_balance: "" });
    setShowForm(true);
  };

  const requestDelete = (account) => {
    const label = account.name || "esta conta sem nome";
    if (window.confirm(`Excluir ${label}? A exclusão só será permitida se não houver transações ou compromissos ligados a ela.`)) {
      remove.mutate(account.id);
    }
  };

  return (
    <div data-testid="accounts-page">
      <PageHeader
        subtitle="Contas e saldo"
        title="Suas contas"
        right={
          <button
            data-testid="new-account-btn"
            onClick={() => {
              if (showForm && !editingId) reset();
              else {
                setEditingId(null);
                setForm(emptyForm);
                setShowForm(true);
              }
            }}
            className="flex items-center gap-1.5 rounded-md bg-[#ccff00] px-3.5 py-2 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
          >
            <Plus size={15} /> Nova conta
          </button>
        }
      />

      {free && (
        <div className="mb-5 grid gap-4 sm:grid-cols-3">
          <Metric label="Saldo total" value={brl(free.balance)} testid="accounts-balance" />
          <Metric label="Pendente do mês" value={brl(free.pending_commitments)} tone="expense" testid="accounts-pending" />
          <Metric label="Livre agora" value={brl(free.free_now)} tone="free" testid="accounts-free" />
        </div>
      )}

      {showForm && (
        <form
          className="surface mb-5 grid gap-3 rounded-lg p-5 sm:grid-cols-4"
          data-testid="account-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!save.isPending) save.mutate();
          }}
        >
          <input
            className={field}
            placeholder="Nome (ex.: Itaú)"
            data-testid="account-name"
            autoFocus
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <select className={field} data-testid="account-type" value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value })}>
            <option value="checking">Conta corrente</option>
            <option value="savings">Poupança</option>
            <option value="cash">Dinheiro</option>
            <option value="wallet">Carteira digital</option>
            <option value="other">Outra</option>
          </select>
          {!editingId ? (
            <input
              className={`${field} num`}
              placeholder="Saldo inicial (ex.: 1234,56)"
              inputMode="decimal"
              data-testid="account-balance-input"
              value={form.opening_balance}
              onChange={(e) => setForm({ ...form, opening_balance: e.target.value })}
            />
          ) : (
            <div className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-xs text-zinc-500">
              O saldo não é alterado aqui. Ele muda por transações reais.
            </div>
          )}
          <div className="flex gap-2">
            <button type="submit" data-testid="account-save" disabled={save.isPending}
              className="flex-1 rounded-md bg-[#ccff00] py-2.5 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50">
              {editingId ? "Salvar" : "Criar"}
            </button>
            <button type="button" onClick={reset} title="Cancelar"
              className="rounded-md border border-zinc-800 px-3 text-zinc-400 hover:bg-zinc-800">
              <X size={15} />
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <Skeleton className="h-24" />
      ) : accounts.length === 0 ? (
        <EmptyState title="Nenhuma conta cadastrada" description="O saldo das contas é a base do cálculo de dinheiro livre." testid="accounts-empty" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 stagger">
          {accounts.map((account) => (
            <div key={account.id} className="surface rounded-lg p-5" data-testid={`account-${account.id}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-sm text-zinc-300">
                    <Wallet size={15} style={{ color: account.color }} />
                    <span className={account.name ? "" : "italic text-amber-300"}>
                      {account.name || "Conta sem nome"}
                    </span>
                  </p>
                  <p className="num mt-2 text-2xl font-semibold text-zinc-50">{brl(account.current_balance)}</p>
                  <p className="mt-1 text-[11px] text-zinc-500">Alterado apenas por transações reais.</p>
                </div>
                <div className="flex gap-1.5">
                  <button data-testid={`account-edit-${account.id}`} onClick={() => startEdit(account)} title="Editar conta"
                    className="rounded-md border border-zinc-800 p-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100">
                    <Pencil size={14} />
                  </button>
                  <button data-testid={`account-delete-${account.id}`} onClick={() => requestDelete(account)} title="Excluir conta"
                    className="rounded-md border border-zinc-800 p-2 text-rose-400 hover:bg-rose-400/10">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
