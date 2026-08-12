import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowDownLeft, ArrowUpRight, Plus, UserPlus } from "lucide-react";
import { apiError, brl, http } from "@/lib/api";
import { EmptyState, Metric, PageHeader, Skeleton } from "@/components/ui-kit/Primitives";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#ccff00]";

export default function ThirdParties() {
  const [personName, setPersonName] = useState("");
  const [form, setForm] = useState({
    person_id: "", direction: "receivable", description: "", total_amount: "",
    installments: "1", credit_card_id: "",
  });
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

  const createPerson = useMutation({
    mutationFn: async () => http.post("/people", { name: personName }),
    onSuccess: () => {
      toast.success("Pessoa cadastrada");
      setPersonName("");
      queryClient.invalidateQueries({ queryKey: ["people"] });
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const create = useMutation({
    mutationFn: async () =>
      http.post("/third-parties", {
        person_id: form.person_id,
        direction: form.direction,
        description: form.description,
        total_amount: Number(form.total_amount),
        installments: Number(form.installments || 1),
        credit_card_id: form.credit_card_id || null,
      }),
    onSuccess: () => {
      toast.success("Registro de terceiro criado");
      queryClient.invalidateQueries();
      setForm({ person_id: "", direction: "receivable", description: "", total_amount: "",
        installments: "1", credit_card_id: "" });
    },
    onError: (e) => toast.error(apiError(e)),
  });

  return (
    <div data-testid="third-parties-page">
      <PageHeader subtitle="Dinheiro de outras pessoas" title="Terceiros" />

      {data && (
        <div className="mb-5 grid gap-4 sm:grid-cols-2">
          <Metric
            label="Tenho a receber"
            value={brl(data.total_receivable)}
            tone="income"
            testid="tp-receivable"
          />
          <Metric
            label="Tenho a pagar"
            value={brl(data.total_payable)}
            tone="expense"
            testid="tp-payable"
          />
        </div>
      )}

      <div className="surface mb-5 rounded-lg p-5">
        <p className="label-caps mb-3">Nova pessoa</p>
        <div className="flex gap-2">
          <input
            className={field}
            placeholder="Nome (ex.: Ana)"
            data-testid="person-name"
            value={personName}
            onChange={(e) => setPersonName(e.target.value)}
          />
          <button
            data-testid="person-save"
            onClick={() => createPerson.mutate()}
            className="flex items-center gap-1.5 whitespace-nowrap rounded-md border border-zinc-800 px-3.5 text-sm text-zinc-200 transition-colors hover:bg-zinc-800"
          >
            <UserPlus size={15} /> Cadastrar
          </button>
        </div>
      </div>

      <div className="surface mb-6 grid gap-3 rounded-lg p-5 lg:grid-cols-3" data-testid="tp-form">
        <select
          className={field}
          data-testid="tp-person"
          value={form.person_id}
          onChange={(e) => setForm({ ...form, person_id: e.target.value })}
        >
          <option value="">Pessoa</option>
          {people.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <select
          className={field}
          data-testid="tp-direction"
          value={form.direction}
          onChange={(e) => setForm({ ...form, direction: e.target.value })}
        >
          <option value="receivable">Tenho a receber</option>
          <option value="payable">Tenho a pagar</option>
        </select>
        <input
          className={field}
          placeholder="Descrição"
          data-testid="tp-description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <input
          className={`${field} num`}
          placeholder="Valor total"
          data-testid="tp-amount"
          value={form.total_amount}
          onChange={(e) => setForm({ ...form, total_amount: e.target.value })}
        />
        <input
          className={`${field} num`}
          placeholder="Parcelas"
          data-testid="tp-installments"
          value={form.installments}
          onChange={(e) => setForm({ ...form, installments: e.target.value })}
        />
        <select
          className={field}
          data-testid="tp-card"
          value={form.credit_card_id}
          onChange={(e) => setForm({ ...form, credit_card_id: e.target.value })}
        >
          <option value="">Sem cartão</option>
          {cards.map((c) => (
            <option key={c.id} value={c.id}>
              Usou meu cartão {c.name}
            </option>
          ))}
        </select>
        <button
          data-testid="tp-save"
          onClick={() => create.mutate()}
          className="flex items-center justify-center gap-1.5 rounded-md bg-[#ccff00] py-2.5 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] lg:col-span-3"
        >
          <Plus size={15} /> Registrar terceiro
        </button>
        <p className="text-[11px] text-zinc-500 lg:col-span-3">
          Ao usar seu cartão, o sistema cria dois compromissos ligados: a sua obrigação com o banco
          (saída, na fatura) e o valor que a pessoa deve a você (entrada esperada). Sem dupla contagem.
        </p>
      </div>

      {isLoading ? (
        <Skeleton className="h-24" />
      ) : data.items.length === 0 ? (
        <EmptyState
          title="Nenhum registro de terceiros"
          description="Empréstimos, compras de outras pessoas no seu cartão e dívidas com amigos aparecem aqui."
          testid="tp-empty"
        />
      ) : (
        <div className="space-y-2.5 stagger">
          {data.items.map((item) => (
            <div
              key={item.id}
              className="surface flex flex-wrap items-center gap-4 rounded-lg px-5 py-4"
              data-testid={`tp-item-${item.id}`}
            >
              <span
                className={`flex h-9 w-9 items-center justify-center rounded-md ${
                  item.direction === "receivable"
                    ? "bg-emerald-400/10 text-emerald-400"
                    : "bg-rose-400/10 text-rose-400"
                }`}
              >
                {item.direction === "receivable" ? (
                  <ArrowDownLeft size={16} />
                ) : (
                  <ArrowUpRight size={16} />
                )}
              </span>
              <div className="flex-1 min-w-[160px]">
                <p className="text-sm text-zinc-100">
                  {item.person} · {item.description}
                </p>
                <p className="num mt-0.5 text-[11px] text-zinc-500">
                  {item.installments}x · {item.direction === "receivable" ? "a receber" : "a pagar"}
                  {item.card_commitment_id && " · usou meu cartão"}
                </p>
              </div>
              <div className="text-right">
                <p className="num text-sm text-zinc-100">{brl(item.total)}</p>
                <p className="num text-[11px] text-zinc-500">{brl(item.pending)} pendente</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
