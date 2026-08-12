import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Beaker } from "lucide-react";
import { apiError, brl, http, shortCompetence } from "@/lib/api";
import { Metric, PageHeader } from "@/components/ui-kit/Primitives";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#ccff00]";

export default function Simulator() {
  const [form, setForm] = useState({
    description: "", total_amount: "", installments: "12", income_delta: "", prepay: "",
    cancel: [],
  });

  const { data: commitments = [] } = useQuery({
    queryKey: ["commitments", "active"],
    queryFn: async () => (await http.get("/commitments", { params: { status: "active" } })).data,
  });

  const simulate = useMutation({
    mutationFn: async () => {
      const payload = { months: 24 };
      if (Number(form.total_amount) > 0) {
        payload.add_installment_purchase = {
          description: form.description || "Nova compra",
          total_amount: Number(form.total_amount),
          installments: Number(form.installments || 1),
        };
      }
      if (form.income_delta) payload.monthly_income_delta = Number(form.income_delta);
      if (form.prepay) payload.prepay_amount = Number(form.prepay);
      if (form.cancel.length) payload.cancel_commitment_ids = form.cancel;
      return (await http.post("/simulations", payload)).data;
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const result = simulate.data;

  return (
    <div data-testid="simulator-page">
      <PageHeader subtitle="E se..." title="Simulador financeiro" />
      <p className="mb-5 text-sm text-zinc-500">
        Nenhuma simulação altera seus dados reais.
      </p>

      <div className="surface grid gap-3 rounded-lg p-5 lg:grid-cols-3" data-testid="simulator-form">
        <input
          className={field}
          placeholder="Descrição da nova compra"
          data-testid="sim-description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <input
          className={`${field} num`}
          placeholder="Valor da compra"
          data-testid="sim-amount"
          value={form.total_amount}
          onChange={(e) => setForm({ ...form, total_amount: e.target.value })}
        />
        <input
          className={`${field} num`}
          placeholder="Parcelas"
          data-testid="sim-installments"
          value={form.installments}
          onChange={(e) => setForm({ ...form, installments: e.target.value })}
        />
        <input
          className={`${field} num`}
          placeholder="Variação de renda mensal (+/-)"
          data-testid="sim-income-delta"
          value={form.income_delta}
          onChange={(e) => setForm({ ...form, income_delta: e.target.value })}
        />
        <input
          className={`${field} num`}
          placeholder="Antecipar dívida (R$)"
          data-testid="sim-prepay"
          value={form.prepay}
          onChange={(e) => setForm({ ...form, prepay: e.target.value })}
        />
        <select
          className={field}
          data-testid="sim-cancel"
          value={form.cancel[0] || ""}
          onChange={(e) => setForm({ ...form, cancel: e.target.value ? [e.target.value] : [] })}
        >
          <option value="">Cancelar um compromisso...</option>
          {commitments.map((c) => (
            <option key={c.id} value={c.id}>
              {c.description}
            </option>
          ))}
        </select>
        <button
          data-testid="sim-run"
          onClick={() => simulate.mutate()}
          disabled={simulate.isPending}
          className="flex items-center justify-center gap-2 rounded-md bg-[#ccff00] py-2.5 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50 lg:col-span-3"
        >
          <Beaker size={15} /> {simulate.isPending ? "Simulando..." : "Simular"}
        </button>
      </div>

      {result && (
        <div className="mt-6" data-testid="simulator-result">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric
              label="Impacto mensal"
              value={brl(result.impact.monthly_commitment_delta)}
              tone="expense"
              testid="sim-impact-monthly"
            />
            <Metric
              label="Variação do livre"
              value={brl(result.impact.free_delta)}
              tone="free"
              testid="sim-impact-free"
            />
            <Metric
              label="Comprometimento"
              value={`${result.impact.commitment_ratio_before}% → ${result.impact.commitment_ratio_after}%`}
              testid="sim-impact-ratio"
            />
            <Metric
              label="Meses afetados"
              value={result.impact.affected_months}
              tone="muted"
              testid="sim-impact-months"
            />
          </div>

          <div className="surface mt-4 rounded-lg p-5">
            <p className="label-caps mb-2">Leitura</p>
            <p className="text-sm text-zinc-300">{result.impact.risk}</p>
            <ul className="mt-3 space-y-1.5 text-sm text-zinc-400">
              {result.notes.map((note, i) => (
                <li key={i}>· {note}</li>
              ))}
            </ul>
          </div>

          <div className="surface mt-4 overflow-x-auto rounded-lg p-5">
            <p className="label-caps mb-3">Antes x depois (12 primeiros meses)</p>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
                  <th className="pb-2 font-medium">Mês</th>
                  <th className="pb-2 text-right font-medium">Livre hoje</th>
                  <th className="pb-2 text-right font-medium">Livre simulado</th>
                  <th className="pb-2 text-right font-medium">Diferença</th>
                </tr>
              </thead>
              <tbody className="num">
                {result.before.rows.slice(0, 12).map((row, i) => {
                  const after = result.after.rows[i];
                  const diff = after.free - row.free;
                  return (
                    <tr key={row.competence} className="border-t border-white/[0.06]">
                      <td className="py-2.5 text-zinc-300">{shortCompetence(row.competence)}</td>
                      <td className="py-2.5 text-right text-zinc-400">{brl(row.free)}</td>
                      <td className="py-2.5 text-right text-zinc-100">{brl(after.free)}</td>
                      <td
                        className={`py-2.5 text-right ${diff < 0 ? "text-rose-400" : "text-emerald-400"}`}
                      >
                        {brl(diff)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
