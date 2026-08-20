import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ArrowUpRight, Ban, Pencil, Play, Plus, Snowflake, TrendingUp,
} from "lucide-react";
import { apiError, brl, formatDate, http, parseMoneyInput, shortCompetence } from "@/lib/api";
import { EmptyState, Metric, PageHeader, Skeleton } from "@/components/ui-kit/Primitives";
import { CommitmentDetailDrawer } from "@/components/CommitmentDetailDrawer";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 outline-none transition-colors focus:border-[#ccff00]";

const STATUS_LABEL = {
  active: { label: "Ativa", className: "border-emerald-400/40 text-emerald-400" },
  paused: { label: "Pausada", className: "border-slate-400/40 text-slate-300" },
  cancelled: { label: "Cancelada", className: "border-zinc-700 text-zinc-500" },
};

const emptyForm = {
  name: "",
  amount: "",
  periodicity: "monthly",
  billing_day: "10",
  credit_card_id: "",
  account_id: "",
  category_id: "",
  responsible_person_id: "",
};

export default function Subscriptions() {
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [detailId, setDetailId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: async () => (await http.get("/subscriptions")).data,
  });
  const { data: cards = [] } = useQuery({
    queryKey: ["credit-cards"],
    queryFn: async () => (await http.get("/credit-cards")).data,
  });
  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await http.get("/accounts")).data,
  });
  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await http.get("/categories")).data,
  });
  const { data: people = [] } = useQuery({
    queryKey: ["people"],
    queryFn: async () => (await http.get("/people")).data,
  });

  const reset = () => {
    setForm(emptyForm);
    setEditing(null);
    setShowForm(false);
  };

  const save = useMutation({
    mutationFn: async () => {
      const amount = parseMoneyInput(form.amount);
      const billingDay = Number(form.billing_day || 1);
      if (!form.name.trim()) throw new Error("Informe o nome da assinatura");
      if (!Number.isFinite(amount) || amount <= 0) throw new Error("Informe um valor válido");
      if (!Number.isInteger(billingDay) || billingDay < 1 || billingDay > 31) {
        throw new Error("Informe um dia de cobrança entre 1 e 31");
      }
      if (form.responsible_person_id && !form.credit_card_id) {
        throw new Error("Para um terceiro reembolsar a assinatura, selecione um cartão de crédito");
      }

      const body = {
        name: form.name.trim(),
        amount,
        periodicity: form.periodicity,
        billing_day: billingDay,
        category_id: form.category_id || null,
        responsible_person_id: form.responsible_person_id || null,
      };
      if (editing) return http.patch(`/subscriptions/${editing}`, body);
      return http.post("/subscriptions", {
        ...body,
        credit_card_id: form.credit_card_id || null,
        account_id: form.credit_card_id ? null : form.account_id || null,
      });
    },
    onSuccess: () => {
      toast.success(editing ? "Assinatura atualizada" : "Assinatura criada");
      queryClient.invalidateQueries();
      reset();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const changeStatus = useMutation({
    mutationFn: async ({ id, status }) =>
      http.post(`/subscriptions/${id}/status`, { status }),
    onSuccess: (_r, { status }) => {
      toast.success(
        status === "paused" ? "Assinatura e reembolso pausados"
          : status === "active" ? "Assinatura e reembolso reativados" : "Assinatura cancelada",
      );
      queryClient.invalidateQueries();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const startEdit = (sub) => {
    setEditing(sub.id);
    setShowForm(true);
    setForm({
      name: sub.name || "",
      amount: String(sub.amount ?? ""),
      periodicity: sub.periodicity || "monthly",
      billing_day: String(sub.billing_day || 1),
      credit_card_id: sub.credit_card_id || "",
      account_id: sub.account_id || "",
      category_id: sub.category?.id || "",
      responsible_person_id: sub.responsible_person?.id || sub.responsible_person_id || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const summary = data?.summary;

  return (
    <div data-testid="subscriptions-page">
      <PageHeader
        subtitle="Cobranças recorrentes"
        title="Minhas Assinaturas"
        right={
          <button
            data-testid="new-subscription-btn"
            onClick={() => (showForm ? reset() : setShowForm(true))}
            className="flex items-center gap-1.5 rounded-md bg-[#ccff00] px-3.5 py-2 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
          >
            <Plus size={15} /> Nova assinatura
          </button>
        }
      />

      {isLoading || !data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 stagger">
            <Metric label="Total mensal" value={brl(summary.monthly_total)} tone="expense" testid="subs-monthly" />
            <Metric label="Custo anual projetado" value={brl(summary.annual_total)} testid="subs-annual" />
            <Metric
              label="Assinaturas ativas"
              value={summary.active_count}
              hint={`${summary.paused_count} pausadas · ${summary.cancelled_count} canceladas`}
              tone="muted"
              testid="subs-count"
            />
            <Metric
              label="Próxima cobrança"
              value={summary.next_charge ? brl(summary.next_charge.amount) : "—"}
              hint={summary.next_charge ? `${summary.next_charge.name} · ${formatDate(summary.next_charge.date)}` : "Nenhuma cobrança prevista"}
              tone="free"
              testid="subs-next-charge"
            />
          </div>

          {summary.third_party_count > 0 && (
            <div
              className="surface mt-4 rounded-lg border border-emerald-400/20 p-4 text-sm text-zinc-300"
              data-testid="subs-third-party-summary"
            >
              <span className="font-medium text-emerald-300">{summary.third_party_count}</span>{" "}
              {summary.third_party_count === 1 ? "assinatura é" : "assinaturas são"} paga(s) por terceiros no seu cartão.
              {summary.third_party_pending > 0 && (
                <span className="num ml-1 text-zinc-100">{brl(summary.third_party_pending)} a receber até o mês atual.</span>
              )}
            </div>
          )}

          {summary.largest && (
            <div className="surface mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg p-5">
              <p className="text-sm text-zinc-300" data-testid="subs-largest">
                Maior assinatura: <span className="text-zinc-50">{summary.largest.name}</span> —{" "}
                <span className="num">{brl(summary.largest.monthly)}/mês</span>{" "}
                <span className="num text-zinc-500">({brl(summary.largest.annual)}/ano)</span>
              </p>
              <p className="num text-xs text-zinc-500">Você gasta {brl(summary.annual_total)} por ano com assinaturas.</p>
            </div>
          )}

          {summary.price_increases.length > 0 && (
            <div className="mt-4 space-y-2">
              {summary.price_increases.map((change) => (
                <div
                  key={change.name}
                  data-testid={`subs-increase-${change.name}`}
                  className="flex items-center gap-2 rounded-md border border-amber-400/30 bg-amber-400/5 px-4 py-2.5 text-sm text-amber-200"
                >
                  <TrendingUp size={14} /> {change.name} aumentou de {brl(change.from)} para {brl(change.to)}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {showForm && (
        <div className="surface mt-5 grid gap-3 rounded-lg p-5 lg:grid-cols-3" data-testid="subscription-form">
          <div className="lg:col-span-3">
            <p className="label-caps">{editing ? "Editar assinatura" : "Nova assinatura"}</p>
            <p className="mt-1 text-[11px] text-zinc-500">
              Se outra pessoa usa uma assinatura cobrada no seu cartão, selecione o responsável abaixo. A despesa entra uma vez na fatura e o reembolso aparece em Terceiros.
            </p>
          </div>

          <input className={field} placeholder="Nome (ex.: Netflix)" data-testid="subscription-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className={`${field} num`} placeholder="Valor (ex.: 55,90)" inputMode="decimal" data-testid="subscription-amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          <select className={field} data-testid="subscription-periodicity" value={form.periodicity} onChange={(e) => setForm({ ...form, periodicity: e.target.value })} disabled={Boolean(editing)}>
            <option value="monthly">Mensal</option>
            <option value="yearly">Anual</option>
          </select>

          <input className={`${field} num`} placeholder="Dia da cobrança" inputMode="numeric" data-testid="subscription-billing-day" value={form.billing_day} onChange={(e) => setForm({ ...form, billing_day: e.target.value })} />

          {!editing ? (
            <>
              <select
                className={field}
                data-testid="subscription-card"
                value={form.credit_card_id}
                onChange={(e) => setForm({
                  ...form,
                  credit_card_id: e.target.value,
                  account_id: e.target.value ? "" : form.account_id,
                  responsible_person_id: e.target.value ? form.responsible_person_id : "",
                })}
              >
                <option value="">Sem cartão (conta)</option>
                {cards.map((c) => <option key={c.id} value={c.id}>Cartão {c.name}</option>)}
              </select>
              {!form.credit_card_id && (
                <select className={field} data-testid="subscription-account" value={form.account_id} onChange={(e) => setForm({ ...form, account_id: e.target.value })}>
                  <option value="">Conta de débito</option>
                  {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              )}
            </>
          ) : (
            <div className="rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-400">
              Forma de cobrança: {form.credit_card_id ? (cards.find((c) => c.id === form.credit_card_id)?.name ? `Cartão ${cards.find((c) => c.id === form.credit_card_id)?.name}` : "Cartão") : "Conta"}
            </div>
          )}

          {form.credit_card_id && (
            <div className="lg:col-span-3 rounded-lg border border-emerald-400/20 bg-emerald-400/[0.04] p-4">
              <label className="mb-1.5 block text-xs font-medium text-emerald-200">Quem é responsável por pagar esta assinatura?</label>
              <select
                className={field}
                data-testid="subscription-responsible-person"
                value={form.responsible_person_id}
                onChange={(e) => setForm({ ...form, responsible_person_id: e.target.value })}
              >
                <option value="">Eu pago esta assinatura</option>
                {people.map((person) => <option key={person.id} value={person.id}>Terceiro: {person.name || "Pessoa sem nome"}</option>)}
              </select>
              {form.responsible_person_id && (
                <p className="mt-2 text-[11px] text-emerald-200/70" data-testid="subscription-reimbursement-help">
                  A cobrança continuará compondo sua fatura. O mesmo valor será criado como recebível recorrente dessa pessoa, sem duplicar a despesa.
                </p>
              )}
            </div>
          )}

          <select className={field} data-testid="subscription-category" value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
            <option value="">Categoria (opcional)</option>
            {categories.filter((c) => c.kind === "expense").map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>

          <button
            data-testid="subscription-save"
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="rounded-md bg-[#ccff00] py-2.5 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50 lg:col-span-3"
          >
            {editing ? "Salvar alterações" : "Criar assinatura"}
          </button>
        </div>
      )}

      <div className="mt-6">
        {data?.items?.length === 0 ? (
          <EmptyState
            title="Nenhuma assinatura cadastrada"
            description="Spotify, Netflix, academia, softwares... cadastre e cada cobrança futura entra automaticamente em Compromissos do Mês."
            testid="subs-empty"
          />
        ) : (
          <div className="space-y-2.5 stagger">
            {data?.items?.map((sub) => {
              const meta = STATUS_LABEL[sub.status] || STATUS_LABEL.active;
              return (
                <div key={sub.id} className="surface rounded-lg px-5 py-4" data-testid={`subscription-${sub.id}`}>
                  <div className="flex flex-wrap items-center gap-4">
                    <div className="flex-1 min-w-[180px]">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-zinc-100">
                        {sub.name}
                        <span className={`num rounded border px-1.5 py-0.5 text-[10px] ${meta.className}`}>{meta.label}</span>
                        {sub.category && <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">{sub.category.name}</span>}
                        {sub.responsible_person && (
                          <span className="rounded border border-emerald-400/30 bg-emerald-400/5 px-1.5 py-0.5 text-[10px] text-emerald-300" data-testid={`subscription-responsible-${sub.id}`}>
                            {sub.responsible_person.name} reembolsa
                          </span>
                        )}
                      </p>
                      <p className="num mt-1 text-[11px] text-zinc-500">
                        {sub.periodicity === "monthly" ? "mensal" : "anual"} · dia {sub.billing_day} · {sub.payment_source} · desde {shortCompetence(sub.start_competence)}
                      </p>
                      {sub.responsible_person && (
                        <p className="num mt-1 text-[11px] text-emerald-300/70">
                          Reembolso em Terceiros: {brl(sub.reimbursement_pending)} pendente até o mês atual
                        </p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="num text-sm text-zinc-100">{brl(sub.amount)}</p>
                      <p className="num text-[11px] text-zinc-500">{brl(sub.monthly_equivalent)}/mês · {brl(sub.annual_cost)}/ano</p>
                    </div>
                    <div className="text-right">
                      <p className="num text-xs text-zinc-300">{sub.next_charge ? formatDate(sub.next_charge) : "—"}</p>
                      <p className="num text-[11px] text-zinc-500">{sub.future_occurrences} cobranças futuras</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <button data-testid={`subscription-commitments-${sub.id}`} onClick={() => setDetailId(sub.commitment_id)} title="Ver compromissos futuros" className="rounded-md border border-zinc-800 p-2 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"><ArrowUpRight size={14} /></button>
                      <button data-testid={`subscription-edit-${sub.id}`} onClick={() => startEdit(sub)} title="Editar" className="rounded-md border border-zinc-800 p-2 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"><Pencil size={14} /></button>
                      {sub.status === "active" && <button data-testid={`subscription-pause-${sub.id}`} onClick={() => changeStatus.mutate({ id: sub.id, status: "paused" })} title="Pausar" className="rounded-md border border-zinc-800 p-2 text-slate-300 transition-colors hover:bg-zinc-800"><Snowflake size={14} /></button>}
                      {sub.status === "paused" && <button data-testid={`subscription-resume-${sub.id}`} onClick={() => changeStatus.mutate({ id: sub.id, status: "active" })} title="Reativar" className="rounded-md border border-[#ccff00]/40 p-2 text-[#ccff00] transition-colors hover:bg-[#ccff00]/10"><Play size={14} /></button>}
                      {sub.status !== "cancelled" && <button data-testid={`subscription-cancel-${sub.id}`} onClick={() => changeStatus.mutate({ id: sub.id, status: "cancelled" })} title="Cancelar (histórico preservado)" className="rounded-md border border-zinc-800 p-2 text-rose-400 transition-colors hover:bg-rose-400/10"><Ban size={14} /></button>}
                    </div>
                  </div>
                  {sub.paid_occurrences > 0 && (
                    <p className="num mt-2 text-[11px] text-zinc-600" data-testid={`subscription-history-${sub.id}`}>
                      Histórico: {sub.paid_occurrences} cobranças pagas · {brl(sub.total_paid)} no total
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <CommitmentDetailDrawer commitmentId={detailId} onClose={() => setDetailId(null)} />
    </div>
  );
}
