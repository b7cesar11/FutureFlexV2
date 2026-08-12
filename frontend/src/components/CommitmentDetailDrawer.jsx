import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Link2, Snowflake, X } from "lucide-react";
import { apiError, brl, formatDate, http, shortCompetence, STATUS_META } from "@/lib/api";
import { StatusBadge } from "@/components/ui-kit/Primitives";

export const CommitmentDetailDrawer = ({ commitmentId, onClose }) => {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["commitment", commitmentId],
    queryFn: async () => (await http.get(`/commitments/${commitmentId}`)).data,
    enabled: Boolean(commitmentId),
  });

  const freezeMutation = useMutation({
    mutationFn: async (frozen) =>
      http.post(`/commitments/${commitmentId}/${frozen ? "freeze" : "unfreeze"}`),
    onSuccess: (_res, frozen) => {
      toast.success(frozen ? "Compromisso congelado" : "Compromisso descongelado");
      queryClient.invalidateQueries();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  if (!commitmentId) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div
        data-testid="commitment-detail"
        className="relative z-10 h-full w-full sm:max-w-md overflow-y-auto border-l border-white/10 bg-[#0d0d0f] p-6"
      >
        <div className="mb-6 flex items-start justify-between">
          <div>
            <p className="label-caps">Detalhe do compromisso</p>
            <h3 className="mt-1 text-xl font-semibold" data-testid="detail-description">
              {isLoading ? "Carregando..." : data?.description}
            </h3>
          </div>
          <button
            onClick={onClose}
            data-testid="detail-close"
            className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-800"
          >
            <X size={18} />
          </button>
        </div>

        {data && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="surface rounded-lg p-4">
                <p className="label-caps">Valor total</p>
                <p className="num mt-1 text-lg" data-testid="detail-total">
                  {brl(data.total_amount)}
                </p>
              </div>
              <div className="surface rounded-lg p-4">
                <p className="label-caps">Restante</p>
                <p className="num mt-1 text-lg text-rose-400" data-testid="detail-remaining">
                  {brl(data.remaining_amount)}
                </p>
              </div>
              {data.installments_total && (
                <div className="surface rounded-lg p-4">
                  <p className="label-caps">Parcela atual</p>
                  <p className="num mt-1 text-lg" data-testid="detail-current-installment">
                    {Math.min(data.current_installment, data.installments_total)}/
                    {data.installments_total}
                  </p>
                </div>
              )}
              <div className="surface rounded-lg p-4">
                <p className="label-caps">Origem</p>
                <p className="mt-1 text-sm text-zinc-300">{data.credit_card?.name || "Conta / dinheiro"}</p>
              </div>
            </div>

            {data.person && (
              <p className="mt-4 text-sm text-zinc-400">
                Pessoa relacionada: <span className="text-zinc-100">{data.person.name}</span>
              </p>
            )}

            {data.linked_commitment && (
              <div
                className="mt-4 rounded-lg border border-[#ccff00]/25 bg-[#ccff00]/5 p-4"
                data-testid="detail-linked-commitment"
              >
                <p className="flex items-center gap-2 text-xs font-medium text-[#ccff00]">
                  <Link2 size={13} /> Compromisso relacionado
                </p>
                <p className="mt-1.5 text-sm text-zinc-200">{data.linked_commitment.description}</p>
                <p className="num mt-0.5 text-xs text-zinc-400">
                  {data.linked_commitment.direction === "inflow" ? "entrada esperada" : "saída"} ·{" "}
                  {brl(data.linked_commitment.total_amount)}
                </p>
                {data.third_party_responsible && (
                  <p className="mt-2 text-[11px] text-zinc-400">
                    Esta parcela do cartão possui um terceiro responsável.
                  </p>
                )}
              </div>
            )}

            <button
              data-testid="detail-freeze-btn"
              onClick={() => freezeMutation.mutate(!data.frozen)}
              className={`mt-5 flex w-full items-center justify-center gap-2 rounded-md border py-2.5 text-sm transition-colors ${
                data.frozen
                  ? "border-[#ccff00]/40 text-[#ccff00] hover:bg-[#ccff00]/10"
                  : "border-zinc-800 text-zinc-300 hover:bg-zinc-800"
              }`}
            >
              <Snowflake size={15} />
              {data.frozen ? "Descongelar compromisso" : "Congelar compromisso"}
            </button>

            <p className="label-caps mt-7 mb-3">Próximas ocorrências</p>
            <div className="space-y-1.5" data-testid="detail-occurrences">
              {data.occurrences.map((occ) => {
                const meta = STATUS_META[occ.status] || STATUS_META.future;
                return (
                  <div
                    key={occ.id}
                    className={`flex items-center justify-between rounded-md px-3 py-2.5 text-sm ${
                      occ.status === "paid" ? "realizado" : "previsto"
                    }`}
                  >
                    <span className="num text-xs text-zinc-400">
                      {shortCompetence(occ.competence)} · {formatDate(occ.due_date)}
                      {occ.sequence ? ` · ${occ.sequence}/${occ.sequence_total}` : ""}
                    </span>
                    <span className="flex items-center gap-2">
                      <StatusBadge status={occ.status} meta={meta} />
                      <span className="num text-zinc-100">{brl(occ.amount)}</span>
                    </span>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
