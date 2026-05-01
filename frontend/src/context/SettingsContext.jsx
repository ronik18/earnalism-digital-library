import { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";
import { api } from "../lib/api";

const SettingsContext = createContext({ social: {}, refresh: () => {} });

export function SettingsProvider({ children }) {
  const [social, setSocial] = useState({ instagram: "", facebook: "", youtube: "", linkedin: "", twitter: "" });

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/settings/social");
      setSocial(data || {});
    } catch (err) {
      // Non-fatal: defaults remain in place. Surface the failure to the console for diagnosis.
      console.warn("[SettingsContext] failed to load /settings/social:", err?.message || err);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const value = useMemo(() => ({ social, refresh }), [social, refresh]);

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export const useSettings = () => useContext(SettingsContext);
