import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";

const SettingsContext = createContext({ social: {}, refresh: () => {} });

export function SettingsProvider({ children }) {
  const [social, setSocial] = useState({ instagram: "", facebook: "", youtube: "", linkedin: "", twitter: "" });

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/settings/social");
      setSocial(data || {});
    } catch {
      /* ignore — defaults already set */
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return (
    <SettingsContext.Provider value={{ social, refresh }}>
      {children}
    </SettingsContext.Provider>
  );
}

export const useSettings = () => useContext(SettingsContext);
