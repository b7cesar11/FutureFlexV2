import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowDownLeft, ArrowUpRight, Pencil, Plus, Trash2, UserPlus, X } from "lucide-react";
import { apiError, brl, formatDate, http, parseMoneyInput } from "@/lib/api";
import { EmptyState, Metric, PageHeader, Skeleton } from "@/components/ui-kit/Primitives";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#ccff00]";
const emptyForm = {
  person_id: "", direction: "receivable", description: "", total_amount: "",
  installments: "1", credit_card_id: "", start_date: "",
};

export default function ThirdParties() {
  const [personName, setPersonName] = useState("");
  const [editingPersonId, setEditingPersonId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["third-parties"],
    queryFn: async () => (await http.get("/third-parties")).data,
  });
  const { data: people = [] } = useQuery({
    queryKey: ["people"],
    queryFn: async () => (await http.get("/people")).data,
  });
  const { data: cards = [] } = useQuery({
    queryKey: ["credit-cards"],
    queryFn: async () => (await http.get("/credit-cards")).data,
  });

  const savePerson = useMutation({
    mutationFn: async () => {
      const name = personName.trim();
      if (!name) throw new Error("Informe o nome da pessoa");
      return editingPersonId
        ? http.patch(`/people/${editingPersonId}`, { name })
        : http.post("/people", { name });
    },
    onSuccess: () => {
      toast.success(editingPersonId ? "Pessoa atualizada" : "Pessoa cadastrada");
      setPersonName("");
      setEditingPersonId(null);
      queryClient.invalidateQueries();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const deletePerson = useMutation({
    mutationFn: async (id) => http.delete(`/people/${id}`),
    onSuccess: () => {
      toast.success("Pessoa excluída");
      queryClient.invalidateQueries();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const saveThirdParty = useMutation({
    mutationFn: async () => {
      const amount = parseMoneyInput(form.total_amount);
      if (!form.person_id) throw new Error("Selecione a pessoa");
      if (!form.description.trim()) throw new Error("Informe a descrição");
      if (!Number.isFinite(amount) || amount <= 0) throw new Error("Informe um valor válido");
      const installments = Number(form.installments || 1);
      if (!Number.isInteger(installments) || installments < 1) throw new Error("Informe o número de parcelas");
      if (!form.start_date) throw new Error(form.credit_card_id ? "Informe a data da compra" : "Informe o primeiro vencimento");

      const payload = {
        person_id: form.person_id,
        direction: form.direction,
        description: form.description.trim(),
        total_amount: amount,
        installments,
        credit_card_id: form.credit_card_id || null,
        start_date: form.start_date,
      };
      return editingId
        ? http.patch(`/third-parties/${editingId}`, payload)
        : http.post("/third-parties", payload);
    },
    onSuccess: () => {
      toast.success(editingId ? "Registro de terceiro corrigido" : "Registro de terceiro criado");
      queryClient.invalidateQueries();
      setEditingId(null);
      setForm(emptyForm);
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const deleteThirdParty = useMutation({
    mutationFn: async (id) => http.delete(`/third-parties/${id}`),
    onSuccess: () => {
      toast.success("Registro de terceiro excluído");
      queryClient.invalidateQueries();
      setEditingId(null);
      setForm(emptyForm);
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const startEditPerson = (person) => {
    setEditingPersonId(person.id);
    setPersonName(person.name || "");
  };

  const startEditThirdParty = (item) => {
    const date = item.start_date || item.first_due_date || "";
    setEditingId(item.id);
    setForm({
      person_id: item.person_id || "",
      direction: item.direction || "receivable",
      description: item.description || "",
      total_amount: String(item.total_amount ?? item.total ?? ""),
      installments: String(item.installments || 1),
      credit_card_id: item.credit_card_id || "",
      start_date: date ? String(date).slice(0, 10) : "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div data-testid="third-parties-page">
      <PageHeader subtitle="Dinheiro de outras pessoas" title="Terceiros" />

      {data && (
        <div className="mb-5 grid gap-4 sm:grid-cols-2">
          <Metric label="Tenho a receber" value={brl(data.total_receivable)} tone="income" testid="tp-receivable" />
          <Metric label="Tenho a pagar" value={brl(data.total_payable)} tone="expense" testid="tp-payable" />
        </div>
      )}

      <div className="surface mb-5 rounded-lg p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="label-caps">{editingPersonId ? "Editar pessoa" : "Nova pessoa"}</p>
          {editingPersonId && (
            <button onClick={() => { setEditingPersonId(null); setPersonName(""); }} className="text-zinc-500 hover:text-zinc-200">
              <X size={16} />
            </button>
          )}
        </div>
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (!savePerson.isPending) savePerson.mutate(); }}>
          <input className={field} placeholder="Nome (ex.: Ana)" data-testid="person-name"
            value={personName} onChange={(e) => setPersonName(e.target.value)} />
          <button type="submit" data-testid="person-save"
            className="flex items-center gap-1.5 whitespace-nowrap rounded-md border border-zinc-800 px-3.5 text-sm text-zinc-200 hover:bg-zinc-800">
            {editingPersonId ? <Pencil size={15} /> : <UserPlus size={15} />}
            {editingPersonId ? "Salvar" : "Cadastrar"}
          </button>
        </form>

        {people.length > 0 && (
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3" data-testid="people-list">
            {people.map((person) => (
              <div key={person.id} className="flex items-center justify-between gap-2 rounded-md border border-white/[0.07] px-3 py-2.5">
                <span className={`min-w-0 truncate text-sm ${person.name ? "text-zinc-300" : "italic text-amber-300"}`}>
                  {person.name || "Pessoa sem nome"}
                </span>
                <div className="flex gap-1">
                  <button data-testid={`person-edit-${person.id}`} onClick={() => startEditPerson(person)} title="Editar pessoa"
                    className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-100"><Pencil size={13} /></button>
                  <button data-testid={`person-delete-${person.id}`} onClick={() => {
                    if (window.confirm(`Excluir ${person.name || "esta pessoa"}? Só será possível se não houver registros financeiros ligados.`)) deletePerson.mutate(person.id);
                  }} title="Excluir pessoa" className="rounded p-1.5 text-rose-400 hover:bg-rose-400/10"><Trash2 size={13} /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="surface mb-6 grid gap-3 rounded-lg p-5 lg:grid-cols-3" data-testid="tp-form">
        <div className="lg:col-span-3 flex items-center justify-between">
          <p className="label-caps">{editingId ? "Corrigir registro de terceiro" : "Novo registro de terceiro"}</p>
          {editingId && (
            <button onClick={() => { setEditingId(null); setForm(emptyForm); }} className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-200">
              <X size={14} /> Cancelar edição
            </button>
          )}
        </div>
        <select className={field} data-testid="tp-person" value={form.person_id}
          onChange={(e) => setForm({ ...form, person_id: e.target.value })}>
          <option value="">Pessoa</option>
          {people.map((p) => <option key={p.id} value={p.id}>{p.name || "Pessoa sem nome"}</option>)}
        </select>
        <select className={field} data-testid="tp-direction" value={form.direction}
          onChange={(e) => setForm({ ...form, direction: e.target.value })}>
          <option value="receivable">Tenho a receber</option>
          <option value="payable">Tenho a pagar</option>
        </select>
        <input className={field} placeholder="Descrição" data-testid="tp-description" value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input className={`${field} num`} placeholder="Valor total (ex.: 750,35)" inputMode="decimal"
          data-testid="tp-amount" value={form.total_amount}
          onChange={(e) => setForm({ ...form, total_amount: e.target.value })} />
        <input className={`${field} num`} placeholder="Parcelas" inputMode="numeric"
          data-testid="tp-installments" value={form.installments}
          onChange={(e) => setForm({ ...form, installments: e.target.value })} />
        <select className={field} data-testid="tp-card" value={form.credit_card_id}
          onChange={(e) => setForm({ ...form, credit_card_id: e.target.value })}>
          <option value="">Sem cartão</option>
          {cards.map((c) => <option key={c.id} value={c.id}>Usou meu cartão {c.name}</option>)}
        </select>
        <div className="lg:col-span-3">
          <label className="mb-1.5 block text-xs text-zinc-400">
            {form.credit_card_id ? "Data da compra" : "Primeiro vencimento"}
          </label>
          <input type="date" className={field} data-testid="tp-start-date" value={form.start_date}
            onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
          <p className="mt-1 text-[11px] text-zinc-500">
            {form.credit_card_id
              ? "A fatura será determinada pelo ciclo do cartão."
              : "As parcelas seguintes mantêm esse dia nos próximos meses."}
          </p>
        </div>
        <button data-testid="tp-save" onClick={() => saveThirdParty.mutate()} disabled={saveThirdParty.isPending}
          className="flex items-center justify-center gap-1.5 rounded-md bg-[#ccff00] py-2.5 text-sm font-semibold text-black hover:bg-[#b3e600] disabled:opacity-50 lg:col-span-3">
          {editingId ? <Pencil size={15} /> : <Plus size={15} />}
          {editingId ? "Salvar correção" : "Registrar terceiro"}
        </button>
        <p className="text-[11px] text-zinc-500 lg:col-span-3">
          Registros ainda sem pagamento podem ser corrigidos ou excluídos. Depois de uma realização financeira, o histórico fica protegido.
        </p>
      </div>

      {isLoading ? (
        <Skeleton className="h-24" />
      ) : (data?.items || []).length === 0 ? (
        <EmptyState title="Nenhum registro de terceiros" description="Empréstimos, compras de outras pessoas no seu cartão e dívidas com amigos aparecem aqui." testid="tp-empty" />
      ) : (
        <div className="space-y-2.5 stagger">
          {data.items.map((item) => (
            <div key={item.id} className="surface flex flex-wrap items-center gap-4 rounded-lg px-5 py-4" data-testid={`tp-item-${item.id}`}>
              <span className={`flex h-9 w-9 items-center justify-center rounded-md ${item.direction === "receivable" ? "bg-emerald-400/10 text-emerald-400" : "bg-rose-400/10 text-rose-400"}`}>
                {item.direction === "receivable" ? <ArrowDownLeft size={16} /> : <ArrowUpRight size={16} />}
              </span>
              <div className="flex-1 min-w-[180px]">
                <p className="text-sm text-zinc-100">{item.person || "Pessoa sem nome"} · {item.description}</p>
                <p className="num mt-0.5 text-[11px] text-zinc-500">
                  {item.installments}x · {item.direction === "receivable" ? "a receber" : "a pagar"}
                  {item.card_commitment_id && " · usou meu cartão"}
                  {item.first_due_date && ` · 1º venc. ${formatDate(item.first_due_date)}`}
                </p>
              </div>
              <div className="text-right">
                <p className="num text-sm text-zinc-100">{brl(item.total)}</p>
                <p className="num text-[11px] text-zinc-500">{brl(item.pending)} pendente</p>
              </div>
              <div className="flex gap-1.5">
                <button data-testid={`tp-edit-${item.id}`} disabled={!item.editable} onClick={() => startEditThirdParty(item)} title={item.editable ? "Corrigir registro" : "Histórico já realizado"}
                  className="rounded-md border border-zinc-800 p-2 text-zinc-400 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-30">
                  <Pencil size={14} />
                </button>
                <button data-testid={`tp-delete-${item.id}`} disabled={!item.editable} onClick={() => {
                  if (window.confirm("Excluir este registro de terceiro e todos os compromissos ainda não pagos ligados a ele?")) deleteThirdParty.mutate(item.id);
                }} title={item.editable ? "Excluir registro" : "Histórico já realizado"}
                  className="rounded-md border border-zinc-800 p-2 text-rose-400 hover:bg-rose-400/10 disabled:cursor-not-allowed disabled:opacity-30">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
