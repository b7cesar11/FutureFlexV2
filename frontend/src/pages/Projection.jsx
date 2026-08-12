import { useQuery } from "@tanstack/react-query";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { brl, http, shortCompetence } from "@/lib/api";
import { PageHeader, Skeleton } from "@/components/ui-kit/Primitives";

export default function Projection() {
  const { data, isLoading } = useQuery({
    queryKey: ["projection", 24],
    queryFn: async () => (await http.get("/projection", { params: { months: 24 } })).data,
  });

  if (isLoading || !data) return <Skeleton className="h-96" />;

  const chartData = data.rows.map((row) => ({
    name: shortCompetence(row.competence),
    Receitas: row.income,
    Compromissos: row.commitments,
    Livre: row.free,
  }));

  const releases = data.rows.filter((row) => row.released_next_month > 0);

  return (
    <div data-testid="projection-page">
      <PageHeader subtitle="Visão futura" title="Projeção de 24 meses" />

      <div className="surface rounded-lg p-5" data-testid="projection-chart">
        <div className="h-72 w-full min-w-[280px]" style={{ minHeight: 288 }}>
          <ResponsiveContainer width="100%" height="100%" minWidth={280} minHeight={240}>
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="gIncome" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#34D399" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#34D399" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gCommit" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FB7185" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#FB7185" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis
                dataKey="name"
                stroke="#52525b"
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                interval={1}
              />
              <YAxis stroke="#52525b" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} />
              <Tooltip
                contentStyle={{
                  background: "#18181b",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(value) => brl(value)}
              />
              <Area
                type="monotone"
                dataKey="Receitas"
                stroke="#34D399"
                strokeWidth={2}
                fill="url(#gIncome)"
              />
              <Area
                type="monotone"
                dataKey="Compromissos"
                stroke="#FB7185"
                strokeWidth={2}
                fill="url(#gCommit)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {releases.length > 0 && (
        <div className="mt-4 space-y-2">
          {releases.slice(0, 4).map((row) => (
            <div
              key={row.competence}
              data-testid={`release-${row.competence}`}
              className="rounded-md border border-[#ccff00]/25 bg-[#ccff00]/5 px-4 py-3 text-sm text-zinc-200"
            >
              Em {shortCompetence(row.competence)} você libera{" "}
              <span className="num text-[#ccff00]">{brl(row.released_next_month)}/mês</span> porque{" "}
              {row.ending_commitments.length} compromisso(s) terminam.
            </div>
          ))}
        </div>
      )}

      <div className="surface mt-4 overflow-x-auto rounded-lg p-5" data-testid="projection-table">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
              <th className="pb-2 font-medium">Mês</th>
              <th className="pb-2 text-right font-medium">Receitas</th>
              <th className="pb-2 text-right font-medium">Compromissos</th>
              <th className="pb-2 text-right font-medium">Livre</th>
              <th className="pb-2 text-right font-medium">Saldo projetado</th>
              <th className="pb-2 text-right font-medium">Compr.</th>
            </tr>
          </thead>
          <tbody className="num">
            {data.rows.map((row) => (
              <tr
                key={row.competence}
                className="border-t border-white/[0.06]"
                data-testid={`projection-row-${row.competence}`}
              >
                <td className="py-2.5 text-zinc-300">{shortCompetence(row.competence)}</td>
                <td className="py-2.5 text-right text-emerald-400">{brl(row.income)}</td>
                <td className="py-2.5 text-right text-rose-400">{brl(row.commitments)}</td>
                <td className="py-2.5 text-right text-zinc-100">{brl(row.free)}</td>
                <td
                  className={`py-2.5 text-right ${
                    row.projected_balance < 0 ? "text-rose-400" : "text-[#ccff00]"
                  }`}
                >
                  {brl(row.projected_balance)}
                </td>
                <td className="py-2.5 text-right text-zinc-500">{row.commitment_ratio_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
