import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, userApi, TOKEN_KEY, USER_TOKEN_KEY } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // null=loading, false=anonymous, object=signed in
  const [admin, setAdmin] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const adminToken = localStorage.getItem(TOKEN_KEY);
    if (!adminToken) setAdmin(false);
    else api.get("/auth/me")
      .then((r) => setAdmin(r.data))
      .catch(() => { localStorage.removeItem(TOKEN_KEY); setAdmin(false); });

    const userToken = localStorage.getItem(USER_TOKEN_KEY);
    if (!userToken) setUser(false);
    else userApi.get("/users/me")
      .then((r) => setUser(r.data))
      .catch(() => { localStorage.removeItem(USER_TOKEN_KEY); setUser(false); });
  }, []);

  // ---- Admin ----
  const adminLogin = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem(TOKEN_KEY, data.token);
    setAdmin({ email: data.email, role: data.role });
  };
  const adminLogout = () => { localStorage.removeItem(TOKEN_KEY); setAdmin(false); };

  // ---- Reader user ----
  const userSignup = async (name, email, password) => {
    const { data } = await userApi.post("/users/signup", { name, email, password });
    localStorage.setItem(USER_TOKEN_KEY, data.token);
    setUser(data.user);
    return data.user;
  };
  const userLogin = async (email, password) => {
    const { data } = await userApi.post("/users/login", { email, password });
    localStorage.setItem(USER_TOKEN_KEY, data.token);
    setUser(data.user);
    return data.user;
  };
  const userLogout = () => {
    try { userApi.post("/users/logout").catch(() => {}); } catch { /* ignore */ }
    localStorage.removeItem(USER_TOKEN_KEY);
    setUser(false);
  };
  const refreshUser = useCallback(async () => {
    try {
      const { data } = await userApi.get("/users/me");
      setUser(data);
      return data;
    } catch {
      return null;
    }
  }, []);
  const setUserBalance = useCallback((balance) => {
    setUser((u) => (u && typeof u === "object" ? { ...u, reading_seconds_balance: balance } : u));
  }, []);

  return (
    <AuthContext.Provider
      value={{
        admin, user,
        // backwards-compatible aliases (Admin pages used `login`/`logout`)
        login: adminLogin, logout: adminLogout,
        adminLogin, adminLogout,
        userSignup, userLogin, userLogout,
        refreshUser, setUserBalance,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
