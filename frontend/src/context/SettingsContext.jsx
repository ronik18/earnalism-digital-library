import { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";
import { api } from "../lib/api";

const SettingsContext = createContext({ social: {}, brand: {}, refresh: () => {} });

export function SettingsProvider({ children }) {
  const [social, setSocial] = useState({ instagram: "", facebook: "", youtube: "", linkedin: "", twitter: "" });
  const [brand, setBrand] = useState({ logo_url: "", og_image_url: "" });

  const refresh = useCallback(async () => {
    try {
      const [s, b] = await Promise.all([
        api.get("/settings/social"),
        api.get("/settings/brand"),
      ]);
      setSocial(s.data || {});
      setBrand(b.data || {});
    } catch (err) {
      // Non-fatal: defaults remain in place.
      console.warn("[SettingsContext] failed to load public settings:", err?.message || err);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const value = useMemo(() => ({ social, brand, refresh }), [social, brand, refresh]);

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export const useSettings = () => useContext(SettingsContext);
