import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Bot, Eraser, Scissors, Send, ShoppingCart, User } from "lucide-react";
import { apiError, brl, http } from "@/lib/api";
import { PageHeader, Skeleton } from "@/components/ui-kit/Primitives";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 outline-none transition-colors focus:border-[#ccff00]";

const SUGGESTIONS = [
  "Quanto posso gastar sem comprometer minhas contas?",
  "Por que meu dinheiro livre está baixo?",
  "Quais assinaturas estão pesando mais?",
  "Como estará minha situação daqui a 6 meses?",
  "Quais parcelas terminam em breve?",
];

const IMPACT_META = {
  alto: { label: "ALTO IMPACTO", className: "border-rose-400/40 text-rose-300" },
  medio: { label: "MÉDIO IMPACTO", className: "border-amber-400/40 text-amber-300" },
  baixo: { label: "BAIXO IMPACTO", className: "border-zinc-700 text-zinc-400" },
};

export default function AiAnalyst() {
  const [question, setQuestion] = useState("");
  const [purchase, setPurchase] = useState({ amount: "", installments: "10" });
  const [showPurchase, setShowPurchase] = useState(false);
  const bottomRef = useRef(null);
  const queryClient = useQueryClient();

  const { data: conversation, isLoading } = useQuery({
    queryKey: ["ai-conversation"],
    queryFn: async () => (await http.get("/ai/conversations/default")).data,
  });
  const { data: context } = useQuery({
    queryKey: ["ai-context"],
    queryFn: async () => (await http.get("/ai/context")).data,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages?.length]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["ai-conversation"] });

  const ask = useMutation({
    mutationFn: async (text) => (await http.post("/ai/ask", { question: text })).data,
    onSuccess: () => {
      setQuestion("");
      invalidate();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const analyze = useMutation({
    mutationFn: async () =>
      (
        await http.post("/ai/purchase-analysis", {
          amount: Number(purchase.amount),
          installments: Number(purchase.installments || 1),
        })
      ).data,
    onSuccess: () => {
      setShowPurchase(false);
      invalidate();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const cuts = useMutation({
    mutationFn: async () => (await http.post("/ai/cuts", {})).data,
    onSuccess: () => invalidate(),
    onError: (e) => toast.error(apiError(e)),
  });

  const clear = useMutation({
    mutationFn: async () => http.delete("/ai/conversations/default"),
    onSuccess: () => {
      toast.success("Conversa limpa");
      invalidate();
    },
  });

  const busy = ask.isPending || analyze.isPending || cuts.isPending;
  const messages = conversation?.messages || [];
  const lastCuts = cuts.data?.candidates;
  const lastSimulation = analyze.data?.simulation;

  return (
    <div data-testid="ai-page">
      <PageHeader
        subtitle="Seu analista financeiro"
        title="Analista IA"
        right={
          messages.length > 0 && (
            <button
              data-testid="ai-clear"
              onClick={() => clear.mutate()}
              className="flex items-center gap-1.5 rounded-md border border-zinc-800 px-3 py-2 text-xs text-zinc-400 transition-colors hover:bg-zinc-800"
            >
              <Eraser size={13} /> Limpar conversa
            </button>
          )
        }
      />

      {context && (
        <div className="surface mb-5 rounded-lg p-5" data-testid="ai-context-summary">
          <p className="label-caps mb-3">A IA está considerando estes dados reais</p>
          <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Saldo", brl(context.balance)],
              ["Renda prevista", brl(context.month.income_expected)],
              ["Compromissos", brl(context.month.committed)],
              ["Dinheiro livre", brl(context.free_money.free_now)],
              ["Faturas em aberto", context.open_invoices.length],
              ["Assinaturas", brl(context.subscriptions.monthly_total) + "/mês"],
              ["A receber de terceiros", brl(context.third_parties.total_receivable)],
              ["Score de saúde", `${context.health.score}/100`],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between border-b border-white/[0.06] pb-2">
                <span className="text-zinc-500">{label}</span>
                <span className="num text-zinc-200">{value}</span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-zinc-600">
            A IA é analista: ela não paga, não transfere, não cancela e não altera nada. Toda
            simulação é somente leitura.
          </p>
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          data-testid="ai-purchase-toggle"
          onClick={() => setShowPurchase((s) => !s)}
          className="flex items-center gap-1.5 rounded-full border border-zinc-800 px-3.5 py-2 text-xs text-zinc-300 transition-colors hover:border-zinc-600"
        >
          <ShoppingCart size={13} /> Posso fazer uma compra?
        </button>
        <button
          data-testid="ai-cuts-btn"
          onClick={() => cuts.mutate()}
          disabled={busy}
          className="flex items-center gap-1.5 rounded-full border border-zinc-800 px-3.5 py-2 text-xs text-zinc-300 transition-colors hover:border-zinc-600 disabled:opacity-50"
        >
          <Scissors size={13} /> O que eu posso cortar?
        </button>
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            data-testid={`ai-suggestion-${suggestion.slice(0, 12)}`}
            onClick={() => ask.mutate(suggestion)}
            disabled={busy}
            className="rounded-full border border-zinc-800 px-3.5 py-2 text-xs text-zinc-400 transition-colors hover:border-zinc-600 hover:text-zinc-200 disabled:opacity-50"
          >
            {suggestion}
          </button>
        ))}
      </div>

      {showPurchase && (
        <div className="surface mb-4 grid gap-3 rounded-lg p-5 sm:grid-cols-3" data-testid="ai-purchase-form">
          <input
            className={`${field} num`}
            placeholder="Valor da compra (ex.: 2500)"
            data-testid="ai-purchase-amount"
            value={purchase.amount}
            onChange={(e) => setPurchase({ ...purchase, amount: e.target.value })}
          />
          <input
            className={`${field} num`}
            placeholder="Parcelas (1 = à vista)"
            data-testid="ai-purchase-installments"
            value={purchase.installments}
            onChange={(e) => setPurchase({ ...purchase, installments: e.target.value })}
          />
          <button
            data-testid="ai-purchase-analyze"
            onClick={() => analyze.mutate()}
            disabled={busy}
            className="rounded-md bg-[#ccff00] py-2.5 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50"
          >
            Analisar impacto
          </button>
        </div>
      )}

      <div className="surface rounded-lg p-5" data-testid="ai-conversation">
        {isLoading ? (
          <Skeleton className="h-24" />
        ) : messages.length === 0 ? (
          <div className="py-10 text-center">
            <Bot size={26} className="mx-auto text-zinc-700" />
            <p className="mt-3 text-sm text-zinc-400">
              Pergunte sobre a sua própria situação financeira.
            </p>
            <p className="mx-auto mt-1 max-w-md text-xs text-zinc-600">
              As respostas usam somente os seus dados reais. Se faltar informação, a IA vai dizer
              claramente em vez de inventar.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, i) => (
              <div
                key={i}
                className={`flex gap-3 ${message.role === "user" ? "justify-end" : ""}`}
                data-testid={`ai-message-${message.role}-${i}`}
              >
                {message.role === "assistant" && (
                  <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[#ccff00]/10 text-[#ccff00]">
                    <Bot size={14} />
                  </span>
                )}
                <div
                  className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-4 py-3 text-sm leading-relaxed ${
                    message.role === "user"
                      ? "bg-zinc-800 text-zinc-100"
                      : "border border-white/[0.07] bg-zinc-900/60 text-zinc-200"
                  }`}
                >
                  {message.content}
                </div>
                {message.role === "user" && (
                  <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-zinc-800 text-zinc-400">
                    <User size={14} />
                  </span>
                )}
              </div>
            ))}
            {busy && (
              <p className="num text-sm text-[#ccff00]" data-testid="ai-thinking">
                analisando seus dados···
              </p>
            )}
            <div ref={bottomRef} />
          </div>
        )}

        <div className="mt-5 flex gap-2">
          <input
            className={field}
            placeholder="Pergunte algo sobre suas finanças..."
            data-testid="ai-question-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && question.trim() && !busy) ask.mutate(question.trim());
            }}
          />
          <button
            data-testid="ai-send"
            onClick={() => question.trim() && ask.mutate(question.trim())}
            disabled={busy || !question.trim()}
            className="flex items-center gap-1.5 rounded-md bg-[#ccff00] px-4 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50"
          >
            <Send size={15} />
          </button>
        </div>
      </div>

      {lastSimulation && (
        <div className="surface mt-4 rounded-lg p-5" data-testid="ai-simulation-result">
          <p className="label-caps mb-3">Simulação usada (somente leitura)</p>
          <div className="grid gap-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-zinc-500">Impacto mensal</p>
              <p className="num text-rose-400">
                {brl(lastSimulation.impact.monthly_commitment_delta)}
              </p>
            </div>
            <div>
              <p className="text-zinc-500">Variação do livre</p>
              <p className="num text-[#ccff00]">{brl(lastSimulation.impact.free_delta)}</p>
            </div>
            <div>
              <p className="text-zinc-500">Comprometimento</p>
              <p className="num text-zinc-200">
                {lastSimulation.impact.commitment_ratio_before}% →{" "}
                {lastSimulation.impact.commitment_ratio_after}%
              </p>
            </div>
            <div>
              <p className="text-zinc-500">Meses afetados</p>
              <p className="num text-zinc-200">{lastSimulation.impact.affected_months}</p>
            </div>
          </div>
          <p className="mt-3 text-xs text-zinc-500">{lastSimulation.impact.risk}</p>
        </div>
      )}

      {lastCuts && lastCuts.candidates.length > 0 && (
        <div className="surface mt-4 rounded-lg p-5" data-testid="ai-cuts-result">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
            <p className="label-caps">Candidatos a corte (calculados pelo sistema)</p>
            <p className="num text-sm text-[#ccff00]">
              até {brl(lastCuts.potential_monthly_saving)}/mês ·{" "}
              {brl(lastCuts.potential_annual_saving)}/ano
            </p>
          </div>
          <div className="space-y-2">
            {lastCuts.candidates.map((candidate) => {
              const meta = IMPACT_META[candidate.impact];
              return (
                <div
                  key={`${candidate.type}-${candidate.name}`}
                  className="flex flex-wrap items-center gap-3 rounded-md border border-white/[0.07] px-4 py-3 text-sm"
                  data-testid={`cut-${candidate.name}`}
                >
                  <span className={`num rounded border px-1.5 py-0.5 text-[10px] ${meta.className}`}>
                    {meta.label}
                  </span>
                  <span className="flex-1 min-w-[140px] text-zinc-100">
                    {candidate.name}
                    {candidate.essential && (
                      <span className="ml-2 rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                        essencial
                      </span>
                    )}
                  </span>
                  <span className="num text-zinc-300">{brl(candidate.monthly)}/mês</span>
                  <span className="num text-zinc-500">
                    economia anual {brl(candidate.annual_saving)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
