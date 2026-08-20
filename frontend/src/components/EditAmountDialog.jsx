import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { X } from "lucide-react";
import { apiError, brl, competenceLabel, http, parseMoneyInput } from "@/lib/api";

const MODES = [
  {
    value: "single",
    label: "Somente este mês",
    hint: "Altera apenas a ocorrência selecionada.",
  },
  {
    value: "this_and_future",
    label: "Este mês e próximos",
    hint: "Aplica aos meses seguintes ainda não personalizados. Ajustes manuais anteriores são preservados.",
  },
  {
    value: "default",
    label: "Alterar valor padrão",
    hint: "Muda o padrão do compromisso. Afeta meses futuros que ainda usam o valor padrão; personalizações são mantidas.",
  },
];

export const EditAmountDialog = ({ target, onClose }) => {
  const [value, setValue] = useState("");
  const [mode, setMode] = useState("single");
  const queryClient = useQueryClient();

  useEffect(() => {
    if (target) {
      setValue(target.amount != null ? String(target.amount) : "");
      setMode("single");
    }
  }, [target]);

  // Parcelamentos têm cronograma fixo: só faz sentido editar a parcela específica.
  const isInstallment = Boolean(target?.sequence_total);
  const modes = isInstallment ? MODES.filter((m) => m.value === "single") : MODES;

  const mutation = useMutation({
    mutationFn: async () => {
      const amount = parseMoneyInput(value);
      if (!Number.isFinite(amount) || amount <= 0) {
        throw new Error("Informe um valor maior que zero");
      }
      return http.patch(`/occurrences/${target.id}`, { amount, mode });
    },
    onSuccess: (res) => {
      const n = res?.data?.affected_occurrences ?? 1;
      toast.success(
        n > 1 ? `Valor atualizado em ${n} meses` : "Valor atualizado",
      );
      queryClient.invalidateQueries();
      onClose();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  if (!target) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div
        data-testid="edit-amount-dialog"
        className="relative z-10 w-full sm:max-w-md rounded-t-2xl sm:rounded-xl border border-white/10 bg-[#0d0d0f] p-6"
      >
        <div className="mb-5 flex items-start justify-between">
          <div>
            <p className="label-caps">Editar valor</p>
            <h3 className="mt-1 text-lg font-semibold" data-testid="edit-amount-label">
              {target.label}
            </h3>
            <p className="num mt-1 text-sm text-zinc-400">
              <span className="capitalize">{competenceLabel(target.competence)}</span>
              {" · atual "}
              {brl(target.amount)}
            </p>
          </div>
          <button
            onClick={onClose}
            data-testid="edit-amount-close"
            className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-800"
          >
            <X size={18} />
          </button>
        </div>

        <label className="mb-1.5 block text-xs text-zinc-400">Novo valor</label>
        <input
          data-testid="edit-amount-input"
          className="num w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#ccff00]"
          placeholder="0,00"
          inputMode="decimal"
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />

        <div className="mt-5 space-y-2" data-testid="edit-amount-modes">
          {modes.map((m) => (
            <label
              key={m.value}
              data-testid={`edit-mode-${m.value}`}
              className={`flex cursor-pointer gap-3 rounded-lg border p-3 transition-colors ${
                mode === m.value
                  ? "border-[#ccff00]/50 bg-[#ccff00]/5"
                  : "border-zinc-800 hover:bg-zinc-800/40"
              }`}
            >
              <input
                type="radio"
                name="edit-amount-mode"
                className="mt-0.5 accent-[#ccff00]"
                checked={mode === m.value}
                onChange={() => setMode(m.value)}
              />
              <span>
                <span className="block text-sm text-zinc-100">{m.label}</span>
                <span className="mt-0.5 block text-[11px] leading-snug text-zinc-500">
                  {m.hint}
                </span>
              </span>
            </label>
          ))}
        </div>

        <div className="mt-6 flex gap-2">
          <button
            onClick={onClose}
            data-testid="edit-amount-cancel"
            className="flex-1 rounded-md border border-zinc-800 py-3 text-sm font-medium text-zinc-300 transition-colors hover:bg-zinc-800"
          >
            Cancelar
          </button>
          <button
            data-testid="edit-amount-save"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            className="flex-1 rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50"
          >
            {mutation.isPending ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </div>
    </div>
  );
};
