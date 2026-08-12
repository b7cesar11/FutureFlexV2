import { ChevronLeft, ChevronRight } from "lucide-react";
import { addMonths, competenceLabel, currentCompetence } from "@/lib/api";
import { useMonth } from "@/contexts/MonthContext";

export const MonthSwitcher = ({ compact = false }) => {
  const { competence, setCompetence } = useMonth();
  const isCurrent = competence === currentCompetence();

  return (
    <div className="flex items-center gap-2" data-testid="month-switcher">
      <button
        data-testid="month-prev"
        onClick={() => setCompetence(addMonths(competence, -1))}
        className="flex h-9 w-9 items-center justify-center rounded-md border border-white/10 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
        aria-label="Mês anterior"
      >
        <ChevronLeft size={16} />
      </button>
      <div className="min-w-[150px] text-center">
        <p
          data-testid="month-label"
          className={`capitalize ${compact ? "text-sm" : "text-base"} font-medium text-zinc-100`}
        >
          {competenceLabel(competence)}
        </p>
        {!isCurrent && (
          <button
            data-testid="month-back-to-current"
            onClick={() => setCompetence(currentCompetence())}
            className="text-[10px] text-[#ccff00] transition-opacity hover:opacity-70"
          >
            voltar ao mês atual
          </button>
        )}
      </div>
      <button
        data-testid="month-next"
        onClick={() => setCompetence(addMonths(competence, 1))}
        className="flex h-9 w-9 items-center justify-center rounded-md border border-white/10 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
        aria-label="Próximo mês"
      >
        <ChevronRight size={16} />
      </button>
    </div>
  );
};
