import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { X } from "lucide-react";
import { apiError, http, parseMoneyInput } from "@/lib/api";

const TYPES = [
  { key: "expense", label: "Gasto avulso" },
  { key: "income", label: "Receita avulsa" },
  { key: "purchase_installment", label: "Compra parcelada" },
  { key: "fixed_expense", label: "Despesa fixa" },
  { key: "subscription", label: "Assinatura" },
  { key: "recurring_income", label: "Receita recorrente" },
  { key: "loan", label: "Empréstimo / dívida" },
  { key: "financing", label: "Financiamento" },
  { key: "third_party", label: "Terceiro" },
  { key: "transfer", label: "Transferência" },
];

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 outline-none transition-colors focus:border-[#ccff00]";

export const QuickAddDrawer = ({ open, onClose }) => {
  const [type, setType] = useState("expense");
  const [form, setForm] = useState({});
  const queryClient = useQueryClient();

  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: async () => (await http.get("/accounts")).data, enabled: open });
  const { data: cards = [] } = useQuery({ queryKey: ["credit-cards"], queryFn: async () => (await http.get("/credit-cards")).data, enabled: open });
  const { data: categories = [] } = useQuery({ queryKey: ["categories"], queryFn: async () => (await http.get("/categories")).data, enabled: open });
  const { data: people = [] } = useQuery({ queryKey: ["people"], queryFn: async () => (await http.get("/people")).data, enabled: open });

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const needsInstallments = ["purchase_installment", "loan", "financing"].includes(type);
  const needsRecurrenceDay = ["fixed_expense", "subscription", "recurring_income"].includes(type);
  const needsScheduleDate = needsInstallments || type === "third_party";
  const isCommitment = !["expense", "income", "transfer"].includes(type);

  const mutation = useMutation({
    mutationFn: async () => {
      const amount = parseMoneyInput(form.amount);
      if (!Number.isFinite(amount) || amount <= 0) throw new Error("Informe um valor válido");
      if (!form.description && type !== "transfer") throw new Error("Informe a descrição");
      if (needsScheduleDate && !form.start_date) {
        throw new Error(form.credit_card_id ? "Informe a data da compra" : "Informe o primeiro vencimento");
      }
      if (needsRecurrenceDay) {
        const day = Number(form.day_of_month || 10);
        if (!Number.isInteger(day) || day < 1 || day > 31) throw new Error("Informe um dia de vencimento entre 1 e 31");
      }

      if (type === "expense" || type === "income") {
        if (!form.account_id) throw new Error("Selecione a conta");
        return http.post("/transactions", { type, amount, account_id: form.account_id,
          category_id: form.category_id || null, description: form.description });
      }
      if (type === "transfer") {
        if (!form.account_id || !form.to_account_id) throw new Error("Selecione as contas de origem e destino");
        return http.post("/transactions", { type, amount, account_id: form.account_id,
          to_account_id: form.to_account_id, description: form.description || "Transferência" });
      }
      if (type === "third_party") {
        if (!form.person_id) throw new Error("Selecione a pessoa");
        return http.post("/third-parties", {
          person_id: form.person_id,
          direction: form.direction || "receivable",
          description: form.description,
          total_amount: amount,
          installments: Number(form.installments || 1),
          credit_card_id: form.credit_card_id || null,
          category_id: form.category_id || null,
          start_date: form.start_date,
        });
      }

      const payload = { type, description: form.description, total_amount: amount, category_id: form.category_id || null };
      if (needsInstallments) {
        payload.installments_total = Number(form.installments || 1);
        payload.start_date = form.start_date;
      }
      if (form.credit_card_id) {
        payload.payment_method = "credit_card";
        payload.credit_card_id = form.credit_card_id;
      } else {
        payload.payment_method = "account";
        payload.default_account_id = form.account_id || null;
      }
      if (needsRecurrenceDay) payload.day_of_month = Number(form.day_of_month || 10);
      return http.post("/commitments", payload);
    },
    onSuccess: () => {
      toast.success("Registrado com sucesso");
      queryClient.invalidateQueries();
      setForm({});
      onClose();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} data-testid="quick-add-overlay" />
      <div data-testid="quick-add-drawer" className="relative z-10 w-full sm:max-w-lg max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-xl border border-white/10 bg-[#0d0d0f] p-6">
        <div className="mb-5 flex items-start justify-between">
          <div><p className="label-caps">Ação rápida</p><h3 className="mt-1 text-xl font-semibold">Registrar</h3></div>
          <button onClick={onClose} data-testid="quick-add-close" className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"><X size={18} /></button>
        </div>

        <div className="mb-5 flex flex-wrap gap-2">
          {TYPES.map((t) => (
            <button key={t.key} data-testid={`quick-add-type-${t.key}`} onClick={() => { setType(t.key); setForm({}); }}
              className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${type === t.key ? "border-[#ccff00] bg-[#ccff00]/10 text-[#ccff00]" : "border-zinc-800 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"}`}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          {type !== "transfer" && <input className={field} placeholder="Descrição" data-testid="quick-add-description" value={form.description || ""} onChange={set("description")} />}
          <div>
            <label className="mb-1.5 block text-xs text-zinc-400">Valor total</label>
            <input className={`${field} num`} placeholder="Ex.: 750,35 ou 750.35" inputMode="decimal" data-testid="quick-add-amount" value={form.amount || ""} onChange={set("amount")} />
          </div>

          {needsInstallments && (
            <div><label className="mb-1.5 block text-xs text-zinc-400">Número de parcelas</label>
              <input className={`${field} num`} placeholder="1" inputMode="numeric" data-testid="quick-add-installments" value={form.installments || ""} onChange={set("installments")} /></div>
          )}

          {type === "third_party" && (
            <>
              <select className={field} data-testid="quick-add-person" value={form.person_id || ""} onChange={set("person_id")}>
                <option value="">Selecione a pessoa</option>{people.map((p) => <option key={p.id} value={p.id}>{p.name || "Pessoa sem nome"}</option>)}
              </select>
              <select className={field} data-testid="quick-add-direction" value={form.direction || "receivable"} onChange={set("direction")}>
                <option value="receivable">Tenho a receber</option><option value="payable">Tenho a pagar</option>
              </select>
              <input className={`${field} num`} placeholder="Parcelas" inputMode="numeric" data-testid="quick-add-tp-installments" value={form.installments || ""} onChange={set("installments")} />
            </>
          )}

          {(isCommitment || type === "third_party") && (
            <select className={field} data-testid="quick-add-card" value={form.credit_card_id || ""} onChange={set("credit_card_id")}>
              <option value="">Sem cartão (conta / dinheiro)</option>{cards.map((c) => <option key={c.id} value={c.id}>Cartão {c.name}</option>)}
            </select>
          )}

          {needsScheduleDate && (
            <div>
              <label className="mb-1.5 block text-xs text-zinc-400">{form.credit_card_id ? "Data da compra" : "Primeiro vencimento"}</label>
              <input type="date" className={`${field} num`} data-testid="quick-add-due-date" value={form.start_date || ""} onChange={set("start_date")} />
              <p className="mt-1 text-[11px] text-zinc-500">
                {form.credit_card_id ? "O vencimento será calculado pelo ciclo do cartão." : "As próximas parcelas mantêm esse dia nos meses seguintes."}
              </p>
            </div>
          )}

          {needsRecurrenceDay && (
            <div><label className="mb-1.5 block text-xs text-zinc-400">Dia do vencimento / cobrança</label>
              <input className={`${field} num`} placeholder="1 a 31" inputMode="numeric" data-testid="quick-add-day" value={form.day_of_month || ""} onChange={set("day_of_month")} /></div>
          )}

          {(!form.credit_card_id || type === "expense" || type === "income" || type === "transfer") && (
            <select className={field} data-testid="quick-add-account" value={form.account_id || ""} onChange={set("account_id")}>
              <option value="">Selecione a conta</option>{accounts.map((a) => <option key={a.id} value={a.id}>{a.name || "Conta sem nome"}</option>)}
            </select>
          )}

          {type === "transfer" && (
            <select className={field} data-testid="quick-add-to-account" value={form.to_account_id || ""} onChange={set("to_account_id")}>
              <option value="">Conta de destino</option>{accounts.map((a) => <option key={a.id} value={a.id}>{a.name || "Conta sem nome"}</option>)}
            </select>
          )}

          <select className={field} data-testid="quick-add-category" value={form.category_id || ""} onChange={set("category_id")}>
            <option value="">Categoria (opcional)</option>
            {categories.filter((c) => ["income", "recurring_income"].includes(type) ? c.kind === "income" : c.kind === "expense")
              .map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        <button data-testid="quick-add-submit" disabled={mutation.isPending} onClick={() => mutation.mutate()}
          className="mt-6 w-full rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black hover:bg-[#b3e600] disabled:opacity-50">
          {mutation.isPending ? "Registrando..." : "Registrar"}
        </button>
        {isCommitment && <p className="mt-3 text-center text-[11px] text-zinc-500">Compromissos alimentam automaticamente os próximos 24 meses.</p>}
      </div>
    </div>
  );
};
