import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  BarChart3, Bot, CalendarClock, CreditCard, HeartPulse, LayoutDashboard, LogOut,
  MoreHorizontal, Plus, Receipt, Repeat, SlidersHorizontal, Snowflake, Users, Wallet, X,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

// Fonte unica da navegacao. Ordem = ordem no sidebar desktop.
export const NAV_ITEMS = [
  { to: "/", label: "Início", icon: LayoutDashboard, testid: "nav-home" },
  { to: "/compromissos", label: "Compromissos do Mês", icon: CalendarClock, testid: "nav-commitments", highlight: true },
  { to: "/transacoes", label: "Transações", icon: Receipt, testid: "nav-transactions" },
  { to: "/contas", label: "Carteira / Contas", icon: Wallet, testid: "nav-accounts" },
  { to: "/cartoes", label: "Cartões", icon: CreditCard, testid: "nav-cards" },
  { to: "/terceiros", label: "Terceiros", icon: Users, testid: "nav-third-parties" },
  { to: "/assinaturas", label: "Assinaturas", icon: Repeat, testid: "nav-subscriptions" },
  { to: "/congelados", label: "Congelados", icon: Snowflake, testid: "nav-frozen" },
  { to: "/saude", label: "Saúde Financeira", icon: HeartPulse, testid: "nav-health" },
  { to: "/projecao", label: "Projeção", icon: BarChart3, testid: "nav-projection" },
  { to: "/simulador", label: "Simulador", icon: SlidersHorizontal, testid: "nav-simulator" },
  { to: "/analista-ia", label: "Analista IA", icon: Bot, testid: "nav-ai" },
];

const byPath = (path) => NAV_ITEMS.find((i) => i.to === path);

// Bottom nav: 4 itens fixos + Compromissos no centro (destaque).
const MOBILE_PRIMARY_LEFT = ["/", "/transacoes"];
const MOBILE_PRIMARY_RIGHT = ["/contas"];
// Tudo o mais fica no menu "Mais".
const MOBILE_MORE = [
  "/cartoes", "/terceiros", "/assinaturas", "/congelados",
  "/saude", "/projecao", "/simulador", "/analista-ia",
];

export const Sidebar = ({ onQuickAdd }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <aside
      data-testid="desktop-sidebar"
      className="hidden md:flex md:w-64 lg:w-72 flex-col border-r border-white/[0.08] bg-[#09090b] fixed inset-y-0 left-0 z-30"
    >
      <div className="px-7 pt-8 pb-6">
        <p className="label-caps">Future Flex</p>
        <h1 className="text-2xl font-semibold tracking-tight mt-1">
          V<span className="text-[#ccff00]">2</span>
        </h1>
      </div>

      <button
        data-testid="sidebar-quick-add"
        onClick={onQuickAdd}
        className="mx-5 mb-6 flex items-center justify-center gap-2 rounded-md bg-[#ccff00] px-4 py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] active:scale-[0.98]"
      >
        <Plus size={16} strokeWidth={2.5} /> Registrar
      </button>

      <nav className="flex-1 overflow-y-auto px-3 space-y-1 pb-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon, testid, highlight }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            data-testid={`${testid}-desktop`}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-4 py-2.5 text-sm transition-colors ${
                isActive
                  ? "bg-zinc-800 text-zinc-50"
                  : highlight
                    ? "text-zinc-100 hover:bg-zinc-900"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
              }`
            }
          >
            <Icon size={17} className={highlight ? "text-[#ccff00]" : ""} />
            <span className={highlight ? "font-semibold" : ""}>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/[0.08] px-5 py-5">
        <p className="text-sm text-zinc-300 truncate" data-testid="sidebar-user-email">
          {user?.profile?.name || user?.email}
        </p>
        <button
          data-testid="logout-btn"
          onClick={async () => {
            await logout();
            navigate("/login");
          }}
          className="mt-3 flex items-center gap-2 text-xs text-zinc-500 transition-colors hover:text-rose-400"
        >
          <LogOut size={14} /> Sair
        </button>
      </div>
    </aside>
  );
};

const MoreSheet = ({ open, onClose, onQuickAdd }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!open) return null;

  const items = MOBILE_MORE.map(byPath).filter(Boolean);

  return (
    <div className="fixed inset-0 z-50 md:hidden" data-testid="mobile-more-sheet">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
        data-testid="mobile-more-overlay"
      />
      <div className="absolute inset-x-0 bottom-0 max-h-[85vh] overflow-y-auto rounded-t-2xl border-t border-white/10 bg-[#0d0d0f] p-6 pb-8">
        <div className="mb-5 flex items-center justify-between">
          <p className="text-lg font-semibold">Mais</p>
          <button
            onClick={onClose}
            data-testid="mobile-more-close"
            className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
          >
            <X size={18} />
          </button>
        </div>

        <button
          data-testid="mobile-more-quick-add"
          onClick={() => {
            onClose();
            onQuickAdd();
          }}
          className="mb-5 flex w-full items-center justify-center gap-2 rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600]"
        >
          <Plus size={16} strokeWidth={2.5} /> Registrar
        </button>

        <div className="grid grid-cols-2 gap-2.5">
          {items.map(({ to, label, icon: Icon, testid }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={`${testid}-more`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg border px-4 py-3 text-sm transition-colors ${
                  isActive
                    ? "border-[#ccff00]/40 bg-[#ccff00]/10 text-[#ccff00]"
                    : "border-zinc-800 text-zinc-300 hover:bg-zinc-800"
                }`
              }
            >
              <Icon size={17} /> {label}
            </NavLink>
          ))}
        </div>

        <button
          data-testid="mobile-more-logout"
          onClick={async () => {
            onClose();
            await logout();
            navigate("/login");
          }}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-md border border-zinc-800 py-3 text-xs text-zinc-400 transition-colors hover:text-rose-400"
        >
          <LogOut size={14} /> Sair {user?.email ? `(${user.email})` : ""}
        </button>
      </div>
    </div>
  );
};

export const BottomNav = ({ onQuickAdd }) => {
  const [moreOpen, setMoreOpen] = useState(false);

  const tab = (entry) => {
    const Icon = entry.icon;
    return (
      <NavLink
        key={entry.to}
        to={entry.to}
        end={entry.to === "/"}
        data-testid={`${entry.testid}-mobile`}
        className={({ isActive }) =>
          `flex flex-col items-center gap-1 px-1 py-2 text-[10px] transition-colors ${
            isActive ? "text-[#ccff00]" : "text-zinc-500"
          }`
        }
      >
        <Icon size={19} strokeWidth={2} />
        <span className="truncate max-w-[64px]">{entry.label}</span>
      </NavLink>
    );
  };

  const left = MOBILE_PRIMARY_LEFT.map(byPath).filter(Boolean);
  const right = MOBILE_PRIMARY_RIGHT.map(byPath).filter(Boolean);
  const commitments = byPath("/compromissos");

  return (
    <>
      <MoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} onQuickAdd={onQuickAdd} />
      <nav
        data-testid="mobile-bottom-nav"
        className="md:hidden fixed bottom-0 inset-x-0 z-40 glass border-t border-white/10"
      >
        <div className="grid grid-cols-5 items-end px-2 pb-2 pt-1.5">
          {left.map(tab)}

          {/* Centro: Compromissos do Mes em destaque */}
          <div className="flex flex-col items-center">
            <NavLink
              to={commitments.to}
              data-testid="nav-commitments-mobile"
              className={({ isActive }) =>
                `-mt-7 flex h-14 w-14 items-center justify-center rounded-2xl shadow-[0_0_0_6px_rgba(9,9,11,0.9)] transition-transform active:scale-95 ${
                  isActive ? "bg-[#ccff00] text-black" : "bg-zinc-800 text-[#ccff00]"
                }`
              }
              aria-label="Compromissos do Mês"
            >
              <CalendarClock size={26} strokeWidth={2.4} />
            </NavLink>
            <span className="mt-1 text-[10px] font-semibold text-[#ccff00]">Compromissos</span>
          </div>

          {right.map(tab)}

          <button
            data-testid="mobile-more-btn"
            onClick={() => setMoreOpen(true)}
            className="flex flex-col items-center gap-1 px-1 py-2 text-[10px] text-zinc-500 transition-colors hover:text-zinc-300"
          >
            <MoreHorizontal size={19} strokeWidth={2} />
            <span>Mais</span>
          </button>
        </div>
      </nav>
    </>
  );
};
