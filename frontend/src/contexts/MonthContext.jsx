import { createContext, useContext, useState } from "react";
import { currentCompetence } from "@/lib/api";

const MonthContext = createContext(null);

export function MonthProvider({ children }) {
  const [competence, setCompetence] = useState(currentCompetence());
  return (
    <MonthContext.Provider value={{ competence, setCompetence }}>
      {children}
    </MonthContext.Provider>
  );
}

export const useMonth = () => useContext(MonthContext);
