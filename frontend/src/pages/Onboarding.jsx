import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight, Check, PiggyBank, Sparkles, Wallet } from "lucide-react";
import { apiError, brl, http, parseMoneyInput } from "@/lib/api";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-3 text-sm text-zinc-100 outline-none transition-colors focus:border-[#ccff00]";

const ACCOUNT_TYPES = [
  { value: "checking", label: "Conta corrente" },
  { value: "savings", label: "Poupança" },
  { value: "cash", label: "Dinheiro" },
  { value: "wallet", label: "Carteira digital" },
];

export default function Onboarding() {
  const [step, setStep] = useState("welcome");
  const [createdAccountId, setCreatedAccountId] = useState(null);
  const [account, setAccount] = useState({ name: "", type: "checking", opening_balance: "" });
  const [income, setIncome] = useState({ description: "", amount: "", day_of_month: "5", category_id: "" });
  const queryClient = useQueryClient();

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await http.get("/categories")).data,
    enabled: step === "income-form",
  });

  const finish = () => {
    // Idempotente: a conta ja existe; o Shell reavalia /accounts e leva ao Dashboard.
    queryClient.invalidateQueries();
  };

  const createAccount = useMutation({
    mutationFn: async () => {
      if (!account.name.trim()) throw new Error("Informe o nome da conta");
      const openingBalance = account.opening_balance ? parseMoneyInput(account.opening_balance) : 0;
      if (!Number.isFinite(openingBalance)) throw new Error("Informe um saldo inicial válido");
      const { data } = await http.post("/accounts", {
        name: account.name.trim(),
        type: account.type,
        opening_balance: openingBalance,
      });
      return data;
    },
    onSuccess: (data) => {
      setCreatedAccountId(data?.id || null);
      toast.success("Conta criada");
      setStep("income-ask");
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const createIncome = useMutation({
    mutationFn: async () => {
      const amount = parseMoneyInput(income.amount);
      if (!income.description.trim()) throw new Error("Informe o nome da renda");
      if (!Number.isFinite(amount) || amount <= 0) throw new Error("Informe um valor válido");
      return http.post("/commitments", {
        type: "recurring_income",
        description: income.description.trim(),
        total_amount: amount,
        payment_method: "account",
        default_account_id: createdAccountId,
        day_of_month: Number(income.day_of_month || 5),
        category_id: income.category_id || null,
      });
    },
    onSuccess: () => {
      toast.success("Renda cadastrada — configuração concluída");
      finish();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const StepDots = ({ active }) => (
    <div className="mb-6 flex items-center gap-2" data-testid="onboarding-steps">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className={`h-1.5 rounded-full transition-all ${
            i <= active ? "w-8 bg-[#ccff00]" : "w-4 bg-zinc-700"
          }`}
        />
      ))}
    </div>
  );

  return (
    <div
      className="flex min-h-screen items-center justify-center bg-[#09090b] px-5 py-10"
      data-testid="onboarding-page"
    >
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <p className="label-caps">Future Flex</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">
            V<span className="text-[#ccff00]">2</span>
          </h1>
        </div>

        {step === "welcome" && (
          <div className="surface rounded-2xl p-7 text-center" data-testid="onboarding-welcome">
            <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#ccff00]/10 text-[#ccff00]">
              <Sparkles size={26} />
            </span>
            <h2 className="mt-5 text-2xl font-semibold">Bem-vindo ao Future Flex</h2>
            <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-zinc-400">
              Vamos configurar sua primeira conta em segundos. Depois você poderá adicionar
              cartões, compromissos e assinaturas quando quiser.
            </p>
            <button
              data-testid="onboarding-start"
              onClick={() => setStep("account")}
              className="mt-7 flex w-full items-center justify-center gap-2 rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
            >
              Começar <ArrowRight size={16} />
            </button>
          </div>
        )}

        {step === "account" && (
          <div className="surface rounded-2xl p-7" data-testid="onboarding-account">
            <StepDots active={0} />
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-800 text-[#ccff00]">
              <Wallet size={20} />
            </span>
            <h2 className="mt-4 text-xl font-semibold">Crie sua primeira conta</h2>
            <p className="mt-1 text-sm text-zinc-500">
              O saldo das contas é a base do cálculo de dinheiro livre.
            </p>

            <div className="mt-6 space-y-3">
              <div>
                <label className="mb-1.5 block text-xs text-zinc-400">Nome da conta</label>
                <input
                  className={field}
                  placeholder="Ex.: Itaú, Nubank, Carteira"
                  data-testid="onboarding-account-name"
                  value={account.name}
                  onChange={(e) => setAccount({ ...account, name: e.target.value })}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs text-zinc-400">Tipo</label>
                <select
                  className={field}
                  data-testid="onboarding-account-type"
                  value={account.type}
                  onChange={(e) => setAccount({ ...account, type: e.target.value })}
                >
                  {ACCOUNT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs text-zinc-400">Saldo inicial</label>
                <input
                  className={`${field} num`}
                  placeholder="Ex.: 2500,75"
                  inputMode="decimal"
                  data-testid="onboarding-account-balance"
                  value={account.opening_balance}
                  onChange={(e) => setAccount({ ...account, opening_balance: e.target.value })}
                />
              </div>
            </div>

            <button
              data-testid="onboarding-account-submit"
              disabled={createAccount.isPending}
              onClick={() => createAccount.mutate()}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50"
            >
              {createAccount.isPending ? "Criando..." : (
                <>Continuar <ArrowRight size={16} /></>
              )}
            </button>
          </div>
        )}

        {step === "income-ask" && (
          <div className="surface rounded-2xl p-7 text-center" data-testid="onboarding-income-ask">
            <StepDots active={1} />
            <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-800 text-[#ccff00]">
              <PiggyBank size={20} />
            </span>
            <h2 className="mt-4 text-xl font-semibold">Quer cadastrar uma renda?</h2>
            <p className="mx-auto mt-2 max-w-sm text-sm text-zinc-400">
              Uma renda recorrente (como salário) ajuda a projetar seu dinheiro livre. É opcional —
              você pode fazer isso depois.
            </p>
            <div className="mt-7 space-y-2.5">
              <button
                data-testid="onboarding-income-yes"
                onClick={() => setStep("income-form")}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
              >
                Sim, cadastrar renda
              </button>
              <button
                data-testid="onboarding-income-skip"
                onClick={finish}
                className="w-full rounded-md border border-zinc-800 py-3 text-sm font-medium text-zinc-300 transition-colors hover:bg-zinc-800"
              >
                Pular e ir para o Dashboard
              </button>
            </div>
          </div>
        )}

        {step === "income-form" && (
          <div className="surface rounded-2xl p-7" data-testid="onboarding-income-form">
            <StepDots active={2} />
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-800 text-[#ccff00]">
              <PiggyBank size={20} />
            </span>
            <h2 className="mt-4 text-xl font-semibold">Sua renda recorrente</h2>
            <p className="mt-1 text-sm text-zinc-500">
              Ela entra automaticamente nos próximos meses.
            </p>

            <div className="mt-6 space-y-3">
              <div>
                <label className="mb-1.5 block text-xs text-zinc-400">Nome</label>
                <input
                  className={field}
                  placeholder="Ex.: Salário"
                  data-testid="onboarding-income-name"
                  value={income.description}
                  onChange={(e) => setIncome({ ...income, description: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-xs text-zinc-400">Valor mensal</label>
                  <input
                    className={`${field} num`}
                    placeholder="0,00"
                    inputMode="decimal"
                    data-testid="onboarding-income-amount"
                    value={income.amount}
                    onChange={(e) => setIncome({ ...income, amount: e.target.value })}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-zinc-400">Dia do mês</label>
                  <input
                    className={`${field} num`}
                    placeholder="5"
                    inputMode="numeric"
                    data-testid="onboarding-income-day"
                    value={income.day_of_month}
                    onChange={(e) => setIncome({ ...income, day_of_month: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-xs text-zinc-400">Categoria (opcional)</label>
                <select
                  className={field}
                  data-testid="onboarding-income-category"
                  value={income.category_id}
                  onChange={(e) => setIncome({ ...income, category_id: e.target.value })}
                >
                  <option value="">Sem categoria</option>
                  {categories
                    .filter((c) => c.kind === "income")
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                </select>
              </div>
            </div>

            <button
              data-testid="onboarding-income-submit"
              disabled={createIncome.isPending}
              onClick={() => createIncome.mutate()}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50"
            >
              {createIncome.isPending ? "Concluindo..." : (
                <><Check size={16} /> Concluir configuração</>
              )}
            </button>
            <button
              data-testid="onboarding-income-form-skip"
              onClick={finish}
              className="mt-2.5 w-full rounded-md py-2.5 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-300"
            >
              Pular e ir para o Dashboard
            </button>
          </div>
        )}

        {account.opening_balance !== "" && step === "account" && (
          <p className="mt-4 text-center text-[11px] text-zinc-600">
            Saldo inicial: {Number.isFinite(parseMoneyInput(account.opening_balance))
              ? brl(parseMoneyInput(account.opening_balance))
              : "valor inválido"}
          </p>
        )}
      </div>
    </div>
  );
}
