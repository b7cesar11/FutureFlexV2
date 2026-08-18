import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowRight, Sparkles } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { API, apiError } from "@/lib/api";

const field =
  "w-full rounded-md border border-zinc-800 bg-zinc-900 px-3.5 py-3 text-sm text-zinc-100 outline-none transition-colors focus:border-[#ccff00]";

export default function Login() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_error")) {
      toast.error("Não foi possível concluir o login com o Google.");
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form);
      navigate("/");
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const googleLogin = () => {
    window.location.href = `${API}/auth/google/start`;
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-[1.1fr_0.9fr]">
      <div className="hidden lg:flex flex-col justify-between border-r border-white/[0.08] px-14 py-14">
        <div>
          <p className="label-caps">Future Flex</p>
          <h1 className="mt-2 text-5xl font-semibold tracking-tight">
            V<span className="text-[#ccff00]">2</span>
          </h1>
        </div>
        <div className="max-w-lg">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            Não apenas onde o dinheiro foi.
            <span className="block text-[#ccff00]">Para onde ele está indo.</span>
          </h2>
          <p className="mt-5 text-sm leading-relaxed text-zinc-400">
            Compromissos do mês, parcelas, faturas, assinaturas, terceiros e receitas em um único
            calendário financeiro — com projeção de 24 meses e o quanto realmente está livre.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-4">
            {[
              ["24", "meses de projeção"],
              ["1", "fonte de verdade"],
              ["0", "dupla contagem"],
            ].map(([value, label]) => (
              <div key={label} className="surface rounded-lg p-4">
                <p className="num text-2xl font-semibold text-[#ccff00]">{value}</p>
                <p className="mt-1 text-[11px] leading-tight text-zinc-500">{label}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-zinc-600">Motor financeiro com transações ACID e regras no backend.</p>
      </div>

      <div className="flex items-center justify-center px-6 py-14">
        <div className="w-full max-w-sm">
          <div className="lg:hidden mb-10">
            <p className="label-caps">Future Flex</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">
              V<span className="text-[#ccff00]">2</span>
            </h1>
          </div>

          <h2 className="text-2xl font-semibold tracking-tight">
            {mode === "login" ? "Entrar na sua conta" : "Criar sua conta"}
          </h2>
          <p className="mt-2 text-sm text-zinc-500">
            {mode === "login"
              ? "Acesse seu painel financeiro."
              : "Comece a enxergar seu futuro financeiro."}
          </p>

          <form onSubmit={submit} className="mt-8 space-y-3">
            {mode === "register" && (
              <input
                className={field}
                placeholder="Seu nome"
                data-testid="register-name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            )}
            <input
              className={field}
              type="email"
              required
              placeholder="E-mail"
              data-testid="auth-email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <input
              className={field}
              type="password"
              required
              placeholder="Senha"
              data-testid="auth-password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            <button
              type="submit"
              disabled={busy}
              data-testid="auth-submit"
              className="flex w-full items-center justify-center gap-2 rounded-md bg-[#ccff00] py-3 text-sm font-semibold text-black transition-colors hover:bg-[#b3e600] disabled:opacity-50"
            >
              {busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
              <ArrowRight size={16} />
            </button>
          </form>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-white/10" />
            <span className="text-[10px] uppercase tracking-widest text-zinc-600">ou</span>
            <div className="h-px flex-1 bg-white/10" />
          </div>

          <button
            onClick={googleLogin}
            data-testid="google-login-btn"
            className="flex w-full items-center justify-center gap-2 rounded-md border border-zinc-800 bg-zinc-900 py-3 text-sm text-zinc-200 transition-colors hover:bg-zinc-800"
          >
            <Sparkles size={15} className="text-[#ccff00]" /> Continuar com Google
          </button>

          <button
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            data-testid="auth-toggle-mode"
            className="mt-7 w-full text-center text-sm text-zinc-500 transition-colors hover:text-zinc-300"
          >
            {mode === "login" ? "Não tem conta? Criar agora" : "Já tenho conta. Entrar"}
          </button>
        </div>
      </div>
    </div>
  );
}
