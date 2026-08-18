import axios from "axios";

const configuredBase = (process.env.REACT_APP_BACKEND_URL || "").trim();

// Same-origin is the safest production default when frontend and backend share a host.
// For split deployments, set REACT_APP_BACKEND_URL explicitly (e.g. https://api.example.com).
const BASE = configuredBase.replace(/\/$/, "");
export const API = BASE ? `${BASE}/api` : "/api";

export const http = axios.create({ baseURL: API, withCredentials: true, timeout: 20000 });

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
let csrfToken = null;

function captureCsrf(response) {
  const token = response?.headers?.["x-csrf-token"];
  if (typeof token === "string" && token) csrfToken = token;
}

http.interceptors.request.use((config) => {
  const method = String(config.method || "GET").toUpperCase();
  if (csrfToken && UNSAFE_METHODS.has(method)) {
    config.headers = config.headers || {};
    config.headers["X-CSRF-Token"] = csrfToken;
  }
  return config;
});

http.interceptors.response.use(
  (response) => {
    captureCsrf(response);
    return response;
  },
  (error) => {
    // A rejected CSRF request returns a fresh/valid token so the next user action can
    // recover without exposing the HttpOnly cookie to JavaScript.
    captureCsrf(error.response);
    if (!error.response && error.code === "ECONNABORTED") {
      error.message = "O servidor demorou para responder. Tente novamente.";
    } else if (!error.response) {
      error.message = "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.";
    }
    return Promise.reject(error);
  },
);

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Algo deu errado. Tente novamente.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export function apiError(e) {
  return formatApiErrorDetail(e?.response?.data?.detail) || e?.message;
}

export const brl = (value) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    Number(value || 0),
  );

export const MONTHS_PT = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

export function competenceLabel(competence) {
  if (!competence) return "";
  const [year, month] = competence.split("-");
  return `${MONTHS_PT[Number(month) - 1]} ${year}`;
}

export function shortCompetence(competence) {
  const [year, month] = competence.split("-");
  return `${MONTHS_PT[Number(month) - 1].slice(0, 3)}/${year.slice(2)}`;
}

export function addMonths(competence, n) {
  const [year, month] = competence.split("-").map(Number);
  const total = year * 12 + (month - 1) + n;
  return `${String(Math.floor(total / 12)).padStart(4, "0")}-${String((total % 12) + 1).padStart(2, "0")}`;
}

export function currentCompetence() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export const formatDate = (value) =>
  value ? new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : "";

export const STATUS_META = {
  future: { label: "Previsto", className: "text-zinc-400 border-white/20 border-dashed" },
  due: { label: "A vencer", className: "text-amber-300 border-amber-400/40" },
  paid: { label: "Pago", className: "text-emerald-400 border-emerald-400/40" },
  overdue: { label: "Atrasado", className: "text-rose-400 border-rose-400/50" },
  frozen: { label: "Congelado", className: "text-slate-400 border-slate-400/40" },
  cancelled: { label: "Cancelado", className: "text-zinc-500 border-zinc-600" },
};
