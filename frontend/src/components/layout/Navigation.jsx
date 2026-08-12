import { NavLink, useNavigate } from "react-router-dom";
import {
  BarChart3, CalendarClock, CreditCard, LayoutDashboard, LogOut, Plus, Receipt,
  Users, Wallet, Repeat,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

export const NAV_ITEMS = [
  { to: "/", label: "Início", icon: LayoutDashboard, testid: "nav-home" },
  { to: "/compromissos", label: "Compromissos", icon: CalendarClock, testid: "nav-commitments", highlight: true },
  { to: "/cartoes", label: "Cartões", icon: CreditCard, testid: "nav-cards" },
  { to: "/contas", label: "Contas", icon: Wallet, testid: "nav-accounts" },
  { to: "/terceiros", label: "Terceiros", icon: Users, testid: "nav-third-parties" },
  { to: "/transacoes", label: "Transações", icon: Receipt, testid: "nav-transactions" },
  { to: "/projecao", label: "Projeção", icon: BarChart3, testid: "nav-projection" },
  { to: "/simulador", label: "Simulador", icon: Repeat, testid: "nav-simulator" },
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
        className="mx-5 mb-8 flex items-center justify-center gap-2 rounded-md bg-[#ccff00] px-4 py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] active:scale-[0.98]"
      >
        <Plus size={16} strokeWidth={2.5} /> Registrar
      </button>

      <nav className="flex-1 overflow-y-auto px-3 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, testid, highlight }) => (
          <NavLink
            key={to}
            to={to}
            data-testid={`${testid}-desktop`}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-4 py-2.5 text-sm transition-colors ${
                isActive
                  ? "bg-zinc-800 text-zinc-50"
                  : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
              }`
            }
          >
            <Icon size={17} className={highlight ? "text-[#ccff00]" : ""} />
            <span className={highlight ? "font-medium text-zinc-100" : ""}>{label}</span>
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

export const BottomNav = ({ onQuickAdd }) => {
  const items = NAV_ITEMS.filter((i) =>
    ["/", "/compromissos", "/cartoes", "/terceiros"].includes(i.to),
  );
  const [first, second, ...rest] = items;

  const item = (entry) => {
    const Icon = entry.icon;
    return (
      <NavLink
        key={entry.to}
        to={entry.to}
        data-testid={`${entry.testid}-mobile`}
        className={({ isActive }) =>
          `flex flex-col items-center gap-1 px-2 py-2 text-[10px] transition-colors ${
            isActive ? "text-[#ccff00]" : "text-zinc-500"
          }`
        }
      >
        {({ isActive }) => (
          <>
            <Icon size={entry.highlight ? 22 : 19} strokeWidth={entry.highlight ? 2.4 : 2} />
            <span className={entry.highlight ? "font-semibold" : ""}>{entry.label}</span>
            {entry.highlight && (
              <span
                className={`h-[3px] w-6 rounded-full transition-colors ${
                  isActive ? "bg-[#ccff00]" : "bg-zinc-700"
                }`}
              />
            )}
          </>
        )}
      </NavLink>
    );
  };

  return (
    <nav
      data-testid="mobile-bottom-nav"
      className="md:hidden fixed bottom-0 inset-x-0 z-40 glass border-t border-white/10"
    >
      <div className="grid grid-cols-5 items-end px-2 pb-2 pt-1.5">
        {item(first)}
        {item(second)}
        <div className="flex justify-center">
          <button
            data-testid="quick-add-fab"
            onClick={onQuickAdd}
            className="-mt-7 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#ccff00] text-black shadow-[0_0_0_6px_rgba(9,9,11,0.9)] transition-transform active:scale-95"
            aria-label="Registrar"
          >
            <Plus size={26} strokeWidth={2.6} />
          </button>
        </div>
        {rest.map(item)}
      </div>
    </nav>
  );
};
