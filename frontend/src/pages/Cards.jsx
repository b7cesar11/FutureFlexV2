import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CreditCard as CardIcon, Plus } from "lucide-react";
import { apiError, brl, formatDate, http, parseMoneyInput, shortCompetence, STATUS_META } from "@/lib/api";
import { EmptyState, PageHeader, Skeleton, StatusBadge } from "@/components/ui-kit/Primitives";
import { PayDialog } from "@/components/PayDialog";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#ccff00]";

export default function Cards() {
  const [form, setForm] = useState({ name: "", limit: "", closing_day: "28", due_day: "5" });
  const [showForm, setShowForm] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [payTarget, setPayTarget] = useState(null);
  const queryClient = useQueryClient();

  const { data: cards = [], isLoading } = useQuery({
    queryKey: ["credit-cards"],
    queryFn: async () => (await http.get("/credit-cards")).data,
  });
  const { data: invoices = [] } = useQuery({
    queryKey: ["invoices"],
    queryFn: async () => (await http.get("/invoices")).data,
  });
  const { data: invoiceDetail } = useQuery({
    queryKey: ["invoice", selectedInvoice],
    queryFn: async () => (await http.get(`/invoices/${selectedInvoice}`)).data,
    enabled: Boolean(selectedInvoice),
  });

  const create = useMutation({
    mutationFn: async () => {
      const limit = form.limit ? parseMoneyInput(form.limit) : 0;
      if (!Number.isFinite(limit) || limit < 0) throw new Error("Informe um limite válido");
      return http.post("/credit-cards", {
        name: form.name,
        limit,
        closing_day: Number(form.closing_day),
        due_day: Number(form.due_day),
      });
    },
    onSuccess: () => {
      toast.success("Cartão criado");
      queryClient.invalidateQueries({ queryKey: ["credit-cards"] });
      setForm({ name: "", limit: "", closing_day: "28", due_day: "5" });
      setShowForm(false);
    },
    onError: (e) => toast.error(apiError(e)),
  });

  return (
    <div data-testid="cards-page">
      <PageHeader
        subtitle="Cartões e faturas"
        title="Seus cartões"
        right={
          <button
            data-testid="new-card-btn"
            onClick={() => setShowForm((s) => !s)}
            className="flex items-center gap-1.5 rounded-md bg-[#ccff00] px-3.5 py-2 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
          >
            <Plus size={15} /> Novo cartão
          </button>
        }
      />

      {showForm && (
        <div className="surface mb-5 grid gap-3 rounded-lg p-5 sm:grid-cols-4" data-testid="card-form">
          <input
            className={field}
            placeholder="Nome (ex.: Nubank)"
            data-testid="card-name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            className={`${field} num`}
            placeholder="Limite (ex.: 5000,00)"
            inputMode="decimal"
            data-testid="card-limit"
            value={form.limit}
            onChange={(e) => setForm({ ...form, limit: e.target.value })}
          />
          <input
            className={`${field} num`}
            placeholder="Dia de fechamento"
            data-testid="card-closing-day"
            value={form.closing_day}
            onChange={(e) => setForm({ ...form, closing_day: e.target.value })}
          />
          <div className="flex gap-2">
            <input
              className={`${field} num`}
              placeholder="Dia de vencimento"
              data-testid="card-due-day"
              value={form.due_day}
              onChange={(e) => setForm({ ...form, due_day: e.target.value })}
            />
            <button
              data-testid="card-save"
              onClick={() => create.mutate()}
              className="rounded-md bg-[#ccff00] px-4 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
            >
              Salvar
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <Skeleton className="h-32" />
      ) : cards.length === 0 ? (
        <EmptyState
          title="Nenhum cartão cadastrado"
          description="Cadastre um cartão para que compras parceladas gerem faturas automaticamente."
          testid="cards-empty"
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3 stagger">
          {cards.map((card) => {
            const cardInvoices = invoices
              .filter((i) => i.credit_card_id === card.id && i.total > 0)
              .sort((a, b) => a.competence.localeCompare(b.competence));
            return (
              <div key={card.id} className="surface rounded-lg p-5" data-testid={`card-${card.id}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="flex items-center gap-2 text-base font-medium text-zinc-100">
                      <CardIcon size={16} style={{ color: card.color }} /> {card.name}
                    </p>
                    <p className="num mt-1 text-xs text-zinc-500">
                      fecha dia {card.closing_day} · vence dia {card.due_day}
                    </p>
                  </div>
                  <p className="num text-xs text-zinc-500">limite {brl(card.limit)}</p>
                </div>

                <p className="label-caps mt-5 mb-2">Faturas</p>
                {cardInvoices.length === 0 && (
                  <p className="text-sm text-zinc-500">Nenhuma fatura com valor.</p>
                )}
                <div className="space-y-1.5">
                  {cardInvoices.slice(0, 6).map((invoice) => (
                    <button
                      key={invoice.id}
                      data-testid={`invoice-${invoice.id}`}
                      onClick={() => setSelectedInvoice(invoice.id)}
                      className="flex w-full items-center justify-between rounded-md border border-white/[0.07] px-3 py-2.5 text-sm transition-colors hover:bg-zinc-800/40"
                    >
                      <span className="num text-xs text-zinc-400">
                        {shortCompetence(invoice.competence)} · vence {formatDate(invoice.due_date)}
                      </span>
                      <span className="flex items-center gap-2">
                        <span
                          className={`num rounded border px-1.5 py-0.5 text-[10px] ${
                            invoice.status === "paid"
                              ? "border-emerald-400/40 text-emerald-400"
                              : "border-white/20 text-zinc-400"
                          }`}
                        >
                          {invoice.status === "paid" ? "Paga" : "Aberta"}
                        </span>
                        <span className="num text-zinc-100">{brl(invoice.total)}</span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {invoiceDetail && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setSelectedInvoice(null)}
          />
          <div
            data-testid="invoice-detail"
            className="relative z-10 h-full w-full sm:max-w-md overflow-y-auto border-l border-white/10 bg-[#0d0d0f] p-6"
          >
            <p className="label-caps">Fatura {invoiceDetail.credit_card?.name}</p>
            <h3 className="mt-1 text-xl font-semibold capitalize">
              {shortCompetence(invoiceDetail.competence)}
            </h3>
            <p className="num mt-3 text-3xl font-semibold" data-testid="invoice-total">
              {brl(invoiceDetail.total)}
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Esta é a obrigação agregada do período. Os itens abaixo são a composição — não somam
              de novo no total do mês.
            </p>

            {invoiceDetail.status !== "paid" && (
              <button
                data-testid="pay-invoice-btn"
                onClick={() =>
                  setPayTarget({
                    id: invoiceDetail.id,
                    kind: "invoice",
                    label: `Fatura ${invoiceDetail.credit_card?.name}`,
                    amount: invoiceDetail.total,
                    paid_amount: invoiceDetail.paid_amount,
                  })
                }
                className="mt-5 w-full rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
              >
                Pagar fatura
              </button>
            )}

            <p className="label-caps mt-7 mb-3">Composição ({invoiceDetail.items.length})</p>
            <div className="space-y-1.5">
              {invoiceDetail.items.map((item) => {
                const meta = STATUS_META[item.status] || STATUS_META.future;
                return (
                  <div
                    key={item.id}
                    className="flex items-center justify-between rounded-md border border-white/[0.07] px-3 py-2.5 text-sm"
                    data-testid={`invoice-item-${item.id}`}
                  >
                    <span>
                      <span className="text-zinc-200">{item.label}</span>
                      <span className="num ml-2 text-[11px] text-zinc-500">
                        {formatDate(item.due_date)}
                      </span>
                    </span>
                    <span className="flex items-center gap-2">
                      <StatusBadge status={item.status} meta={meta} />
                      <span className="num text-zinc-100">{brl(item.amount)}</span>
                    </span>
                  </div>
                );
              })}
            </div>

            <button
              onClick={() => setSelectedInvoice(null)}
              data-testid="invoice-detail-close"
              className="mt-6 w-full rounded-md border border-zinc-800 py-2.5 text-sm text-zinc-300 transition-colors hover:bg-zinc-800"
            >
              Fechar
            </button>
          </div>
        </div>
      )}

      <PayDialog target={payTarget} mode="invoice" onClose={() => setPayTarget(null)} />
    </div>
  );
}
