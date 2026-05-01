import { createContext, useContext, useEffect, useState } from "react";
import { api, TOKEN_KEY } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [admin, setAdmin] = useState(null); // null=loading, false=anon, object=user
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) { setAdmin(false); return; }
    api.get("/auth/me")
      .then((r) => setAdmin(r.data))
      .catch(() => { localStorage.removeItem(TOKEN_KEY); setAdmin(false); });
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem(TOKEN_KEY, data.token);
    setAdmin({ email: data.email, role: data.role });
  };
  const logout = () => { localStorage.removeItem(TOKEN_KEY); setAdmin(false); };

  return (
    <AuthContext.Provider value={{ admin, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
