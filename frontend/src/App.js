import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { MonthProvider } from "@/contexts/MonthContext";
import { BottomNav, Sidebar } from "@/components/layout/Navigation";
import { QuickAddDrawer } from "@/components/QuickAddDrawer";
import { MonthSwitcher } from "@/components/layout/MonthSwitcher";
import { apiError, http } from "@/lib/api";
import Login from "@/pages/Login";
import Onboarding from "@/pages/Onboarding";
import Dashboard from "@/pages/Dashboard";
import Commitments from "@/pages/Commitments";
import Cards from "@/pages/Cards";
import Accounts from "@/pages/Accounts";
import ThirdParties from "@/pages/ThirdParties";
import Transactions from "@/pages/Transactions";
import Projection from "@/pages/Projection";
import Simulator from "@/pages/Simulator";
import Subscriptions from "@/pages/Subscriptions";
import Frozen from "@/pages/Frozen";
import Health from "@/pages/Health";
import AiAnalyst from "@/pages/AiAnalyst";

const Loading = () => (
  <div className="flex min-h-screen items-center justify-center" data-testid="app-loading">
    <p className="num text-3xl text-[#ccff00]">···</p>
  </div>
);

const BootstrapError = ({ error, retrying, onRetry, onLogout }) => (
  <div className="flex min-h-screen items-center justify-center bg-[#09090b] px-5">
    <div className="surface w-full max-w-md rounded-2xl p-7 text-center" data-testid="bootstrap-error">
      <p className="label-caps">Future Flex</p>
      <h1 className="mt-3 text-xl font-semibold">Não foi possível carregar seus dados</h1>
      <p className="mt-2 text-sm leading-relaxed text-zinc-400">
        {apiError(error) || "A conexão com o servidor falhou. Tente novamente."}
      </p>
      <button
        type="button"
        disabled={retrying}
        onClick={onRetry}
        className="mt-6 w-full rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black disabled:opacity-50"
      >
        {retrying ? "Tentando..." : "Tentar novamente"}
      </button>
      <button
        type="button"
        onClick={onLogout}
        className="mt-2 w-full rounded-md py-2.5 text-xs font-medium text-zinc-500 hover:text-zinc-300"
      >
        Voltar ao login
      </button>
    </div>
  </div>
);

const Shell = () => {
  const [quickAdd, setQuickAdd] = useState(false);
  const { logout } = useAuth();

  // Onboarding: usuario sem nenhuma conta financeira e levado ao fluxo inicial.
  // Idempotente: assim que existir >= 1 conta, o onboarding nunca mais aparece.
  const {
    data: accounts,
    isLoading: accountsLoading,
    isFetching: accountsFetching,
    isError: accountsError,
    error: accountsErrorDetail,
    refetch: refetchAccounts,
  } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await http.get("/accounts")).data,
    retry: 1,
  });

  if (accountsLoading) return <Loading />;
  if (accountsError || accounts === undefined) {
    return (
      <BootstrapError
        error={accountsErrorDetail}
        retrying={accountsFetching}
        onRetry={() => refetchAccounts()}
        onLogout={() => logout().catch(() => window.location.assign("/login"))}
      />
    );
  }
  if (Array.isArray(accounts) && accounts.length === 0) return <Onboarding />;

  return (
    <MonthProvider>
      <div className="min-h-screen">
        <Sidebar onQuickAdd={() => setQuickAdd(true)} />
        <header className="glass md:hidden sticky top-0 z-30 flex items-center justify-between border-b border-white/10 px-5 py-3">
          <p className="text-lg font-semibold tracking-tight">
            Future Flex <span className="text-[#ccff00]">V2</span>
          </p>
          <MonthSwitcher compact />
        </header>
        <main className="md:pl-64 lg:pl-72">
          <div className="mx-auto max-w-[1400px] px-5 py-7 pb-28 sm:px-8 sm:py-10 md:pb-12">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/compromissos" element={<Commitments />} />
              <Route path="/cartoes" element={<Cards />} />
              <Route path="/contas" element={<Accounts />} />
              <Route path="/terceiros" element={<ThirdParties />} />
              <Route path="/transacoes" element={<Transactions />} />
              <Route path="/assinaturas" element={<Subscriptions />} />
              <Route path="/congelados" element={<Frozen />} />
              <Route path="/saude" element={<Health />} />
              <Route path="/projecao" element={<Projection />} />
              <Route path="/simulador" element={<Simulator />} />
              <Route path="/analista-ia" element={<AiAnalyst />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>
        <BottomNav onQuickAdd={() => setQuickAdd(true)} />
        <QuickAddDrawer open={quickAdd} onClose={() => setQuickAdd(false)} />
      </div>
    </MonthProvider>
  );
};

const Gate = () => {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Login />;
  return <Shell />;
};

const AppRouter = () => (
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/*" element={<Gate />} />
  </Routes>
);

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
        <Toaster theme="dark" position="top-center" richColors />
      </AuthProvider>
    </BrowserRouter>
  );
}
