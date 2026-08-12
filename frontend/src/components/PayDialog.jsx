import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { X } from "lucide-react";
import { apiError, brl, http } from "@/lib/api";

export const PayDialog = ({ target, onClose, mode = "occurrence" }) => {
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const queryClient = useQueryClient();

  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await http.get("/accounts")).data,
    enabled: Boolean(target),
  });

  const isInvoice = mode === "invoice" || target?.kind === "invoice";

  const mutation = useMutation({
    mutationFn: async () => {
      if (!accountId) throw new Error("Escolha a conta utilizada no pagamento");
      const body = { account_id: accountId };
      if (amount) body.amount = Number(amount);
      const url = isInvoice
        ? `/invoices/${target.refs?.invoice_id || target.id}/pay`
        : `/occurrences/${target.id}/pay`;
      return http.post(url, body, {
        headers: { "Idempotency-Key": `${url}-${Date.now()}` },
      });
    },
    onSuccess: () => {
      toast.success("Pagamento registrado");
      queryClient.invalidateQueries();
      onClose();
      setAccountId("");
      setAmount("");
    },
    onError: (e) => toast.error(apiError(e)),
  });

  if (!target) return null;
  const pending = (target.amount || 0) - (target.paid_amount || 0);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div
        data-testid="pay-dialog"
        className="relative z-10 w-full sm:max-w-md rounded-t-2xl sm:rounded-xl border border-white/10 bg-[#0d0d0f] p-6"
      >
        <div className="mb-5 flex items-start justify-between">
          <div>
            <p className="label-caps">
              {isInvoice ? "Pagar fatura" : target.direction === "inflow" ? "Registrar recebimento" : "Pagar compromisso"}
            </p>
            <h3 className="mt-1 text-lg font-semibold">{target.label || "Fatura"}</h3>
            <p className="num mt-1 text-sm text-zinc-400">{brl(pending)} em aberto</p>
          </div>
          <button
            onClick={onClose}
            data-testid="pay-dialog-close"
            className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-800"
          >
            <X size={18} />
          </button>
        </div>

        <p className="mb-2 text-xs text-zinc-500">
          A conta é escolhida agora — não é fixada no compromisso.
        </p>
        <select
          data-testid="pay-account-select"
          className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#ccff00]"
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
        >
          <option value="">Selecione a conta</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} — {brl(a.current_balance)}
            </option>
          ))}
        </select>

        <input
          data-testid="pay-amount-input"
          className="num mt-3 w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#ccff00]"
          placeholder={`Valor (padrão ${brl(pending)})`}
          inputMode="decimal"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />

        <button
          data-testid="pay-confirm-btn"
          disabled={mutation.isPending}
          onClick={() => mutation.mutate()}
          className="mt-5 w-full rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50"
        >
          {mutation.isPending ? "Registrando..." : "Confirmar pagamento"}
        </button>
      </div>
    </div>
  );
};
