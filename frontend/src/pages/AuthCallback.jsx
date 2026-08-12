import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { http } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function AuthCallback() {
  const hasProcessed = useRef(false);
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [error, setError] = useState(null);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const sessionId = new URLSearchParams(window.location.hash.replace("#", "")).get("session_id");
    if (!sessionId) {
      navigate("/login", { replace: true });
      return;
    }

    (async () => {
      try {
        const { data } = await http.post("/auth/google/session", null, {
          headers: { "X-Session-ID": sessionId },
        });
        setUser(data);
        window.history.replaceState({}, document.title, window.location.pathname);
        navigate("/", { replace: true, state: { user: data } });
      } catch {
        setError("Não foi possível concluir o login com o Google.");
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="flex min-h-screen items-center justify-center px-6" data-testid="auth-callback">
      <div className="text-center">
        <p className="num text-3xl text-[#ccff00]">···</p>
        <p className="mt-4 text-sm text-zinc-400">
          {error || "Concluindo seu acesso seguro..."}
        </p>
        {error && (
          <button
            onClick={() => navigate("/login", { replace: true })}
            className="mt-5 rounded-md border border-zinc-800 px-4 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-800"
          >
            Voltar ao login
          </button>
        )}
      </div>
    </div>
  );
}
