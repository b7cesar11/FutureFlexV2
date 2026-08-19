import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Link2, Pencil, Snowflake, Trash2, X } from "lucide-react";
import { apiError, brl, formatDate, http, shortCompetence, STATUS_META } from "@/lib/api";
import { StatusBadge } from "@/components/ui-kit/Primitives";
import { EditAmountDialog } from "@/components/EditAmountDialog";

export const CommitmentDetailDrawer = ({ commitmentId, onClose }) => {
  const queryClient = useQueryClient();
  const [editTarget, setEditTarget] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setConfirmDelete(false);
    setEditTarget(null);
  }, [commitmentId]);

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

  const deleteMutation = useMutation({
    mutationFn: async () => http.delete(`/commitments/${commitmentId}/mistake`),
    onSuccess: () => {
      toast.success("Cadastro excluído");
      queryClient.invalidateQueries();
      setConfirmDelete(false);
      onClose();
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

            {!confirmDelete ? (
              <button
                data-testid="detail-delete-btn"
                onClick={() => setConfirmDelete(true)}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-md border border-rose-500/30 py-2.5 text-sm text-rose-400 transition-colors hover:bg-rose-500/10"
              >
                <Trash2 size={15} /> Excluir cadastro feito por engano
              </button>
            ) : (
              <div
                className="mt-2 rounded-lg border border-rose-500/30 bg-rose-500/5 p-4"
                data-testid="detail-delete-confirm"
              >
                <p className="text-sm font-medium text-rose-300">Excluir definitivamente este cadastro?</p>
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">
                  Só é permitido quando ainda não houve pagamento ou movimentação financeira. Se houver histórico,
                  o sistema bloqueará a exclusão automaticamente.
                </p>
                <div className="mt-3 flex gap-2">
                  <button
                    data-testid="detail-delete-cancel"
                    onClick={() => setConfirmDelete(false)}
                    className="flex-1 rounded-md border border-zinc-800 py-2 text-xs text-zinc-300 hover:bg-zinc-800"
                  >
                    Voltar
                  </button>
                  <button
                    data-testid="detail-delete-confirm-btn"
                    disabled={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate()}
                    className="flex-1 rounded-md bg-rose-500 py-2 text-xs font-semibold text-white disabled:opacity-50"
                  >
                    {deleteMutation.isPending ? "Excluindo..." : "Excluir definitivamente"}
                  </button>
                </div>
              </div>
            )}

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
                      {occ.amount_source === "override" && (
                        <span
                          data-testid={`detail-override-${occ.id}`}
                          title="Valor ajustado para este mês"
                          className="rounded bg-[#ccff00]/15 px-1 py-0.5 text-[9px] font-medium text-[#ccff00]"
                        >
                          ajustado
                        </span>
                      )}
                      <span className="num text-zinc-100">{brl(occ.amount)}</span>
                      {occ.status !== "paid" && occ.status !== "cancelled" &&
                        occ.status !== "frozen" && (
                        <button
                          data-testid={`detail-edit-amount-${occ.id}`}
                          onClick={() => setEditTarget(occ)}
                          title="Editar valor"
                          className="rounded-md border border-zinc-700 p-1 text-zinc-400 transition-colors hover:border-[#ccff00]/40 hover:text-[#ccff00]"
                        >
                          <Pencil size={12} />
                        </button>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
      <EditAmountDialog target={editTarget} onClose={() => setEditTarget(null)} />
    </div>
  );
};
