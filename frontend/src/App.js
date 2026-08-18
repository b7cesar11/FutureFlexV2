import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { MonthProvider } from "@/contexts/MonthContext";
import { BottomNav, Sidebar } from "@/components/layout/Navigation";
import { QuickAddDrawer } from "@/components/QuickAddDrawer";
import { MonthSwitcher } from "@/components/layout/MonthSwitcher";
import { http } from "@/lib/api";
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

const Shell = () => {
  const [quickAdd, setQuickAdd] = useState(false);

  // Onboarding: usuario sem nenhuma conta financeira e levado ao fluxo inicial.
  // Idempotente: assim que existir >= 1 conta, o onboarding nunca mais aparece.
  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => (await http.get("/accounts")).data,
  });

  if (accountsLoading || accounts === undefined) return <Loading />;
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
