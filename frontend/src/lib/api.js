import axios from "axios";

const configuredBase = (process.env.REACT_APP_BACKEND_URL || "").trim();
const BASE = configuredBase.replace(/\/$/, "");
export const API = BASE ? `${BASE}/api` : "/api";

export const http = axios.create({ baseURL: API, withCredentials: true, timeout: 20000 });

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
let csrfToken = null;
let refreshPromise = null;

function captureCsrf(response) {
  const token = response?.headers?.["x-csrf-token"];
  if (typeof token === "string" && token) csrfToken = token;
}

function isRefreshableAuthFailure(error) {
  if (error?.response?.status !== 401) return false;
  const config = error.config || {};
  if (config._ffRetriedAfterRefresh) return false;
  const url = String(config.url || "");
  return ![
    "/auth/login", "/auth/register", "/auth/refresh", "/auth/google/start", "/auth/google/callback",
  ].some((path) => url.startsWith(path));
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
  async (error) => {
    captureCsrf(error.response);
    if (isRefreshableAuthFailure(error)) {
      const original = error.config;
      original._ffRetriedAfterRefresh = true;
      try {
        if (!refreshPromise) {
          refreshPromise = http.post("/auth/refresh").finally(() => { refreshPromise = null; });
        }
        await refreshPromise;
        return http.request(original);
      } catch (refreshError) {
        return Promise.reject(refreshError);
      }
    }
    if (!error.response && error.code === "ECONNABORTED") {
      error.message = "O servidor demorou para responder. Tente novamente.";
    } else if (!error.response && !error.message) {
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
  const detail = e?.response?.data?.detail;
  if (detail != null) return formatApiErrorDetail(detail);
  return e?.message || "Algo deu errado. Tente novamente.";
}

export function parseMoneyInput(value) {
  if (typeof value === "number") return Number.isFinite(value) ? value : NaN;
  let raw = String(value ?? "").trim();
  if (!raw) return NaN;

  raw = raw.replace(/R\$/gi, "").replace(/\s+/g, "").replace(/[^0-9,.-]/g, "");
  const lastComma = raw.lastIndexOf(",");
  const lastDot = raw.lastIndexOf(".");

  if (lastComma >= 0 && lastDot >= 0) {
    if (lastComma > lastDot) raw = raw.replace(/\./g, "").replace(",", ".");
    else raw = raw.replace(/,/g, "");
  } else if (lastComma >= 0) {
    raw = raw.replace(/\./g, "").replace(",", ".");
  }

  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : NaN;
}

export const brl = (value) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value || 0));

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
  value
    ? new Date(value).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", timeZone: "UTC" })
    : "";

export const STATUS_META = {
  future: { label: "Previsto", className: "text-zinc-400 border-white/20 border-dashed" },
  due: { label: "A vencer", className: "text-amber-300 border-amber-400/40" },
  paid: { label: "Pago", className: "text-emerald-400 border-emerald-400/40" },
  overdue: { label: "Atrasado", className: "text-rose-400 border-rose-400/50" },
  frozen: { label: "Congelado", className: "text-slate-400 border-slate-400/40" },
  cancelled: { label: "Cancelado", className: "text-zinc-500 border-zinc-600" },
};
