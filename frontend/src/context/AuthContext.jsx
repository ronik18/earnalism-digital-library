import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, userApi, TOKEN_KEY, USER_TOKEN_KEY, getUserAuthSessionVersion, isUserAuthSessionCurrent } from "../lib/api";

const AuthContext = createContext(null);

function isConfirmedInvalidUserAuth(error) {
  return error?.response?.status === 401;
}

export function AuthProvider({ children }) {
  // null=loading, false=anonymous, object=signed in
  const [admin, setAdmin] = useState(null);
  const [user, setUser] = useState(null);
  const mountedRef = useRef(false);
  const userAuthGenerationRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const adminToken = localStorage.getItem(TOKEN_KEY);
    if (!adminToken) setAdmin(false);
    else api.get("/auth/me", { skipAuthRedirect: true })
      .then((r) => setAdmin(r.data))
      .catch(() => { localStorage.removeItem(TOKEN_KEY); setAdmin(false); });

    const userToken = localStorage.getItem(USER_TOKEN_KEY);
    if (!userToken) setUser(false);
    else {
      const generation = ++userAuthGenerationRef.current;
      const sessionVersion = getUserAuthSessionVersion();
      userApi.get("/users/me", { skipAuthRedirect: true, timeout: 15000 })
        .then((r) => {
          if (
            mountedRef.current
            && generation === userAuthGenerationRef.current
            && isUserAuthSessionCurrent(sessionVersion)
            && localStorage.getItem(USER_TOKEN_KEY)
          ) {
            setUser(r.data);
          }
        })
        .catch((error) => {
          if (!mountedRef.current || generation !== userAuthGenerationRef.current || !isUserAuthSessionCurrent(sessionVersion) || error.authSuperseded) return;
          // A timeout or transport error is recoverable: do not erase a token
          // simply because startup verification did not finish. A confirmed 401
          // remains fail-closed and clears the local user credential.
          if (isConfirmedInvalidUserAuth(error)) localStorage.removeItem(USER_TOKEN_KEY);
          setUser(false);
        });
    }
  }, []);

  // ---- Admin ----
  const adminLogin = useCallback(async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem(TOKEN_KEY, data.token);
    setAdmin({ email: data.email, role: data.role });
  }, []);
  const adminLogout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setAdmin(false);
  }, []);

  // ---- Reader user ----
  const userSignup = useCallback(async (name, email, password) => {
    const generation = ++userAuthGenerationRef.current;
    const { data } = await userApi.post("/users/signup", { name, email, password });
    if (!mountedRef.current || generation !== userAuthGenerationRef.current) {
      throw new Error("A newer authentication request superseded this sign-up.");
    }
    localStorage.setItem(USER_TOKEN_KEY, data.token);
    setUser(data.user);
    return data.user;
  }, []);
  const userLogin = useCallback(async (email, password) => {
    const generation = ++userAuthGenerationRef.current;
    const { data } = await userApi.post("/users/login", { email, password });
    if (!mountedRef.current || generation !== userAuthGenerationRef.current) {
      throw new Error("A newer authentication request superseded this sign-in.");
    }
    localStorage.setItem(USER_TOKEN_KEY, data.token);
    setUser(data.user);
    return data.user;
  }, []);
  const userLogout = useCallback(() => {
    ++userAuthGenerationRef.current;
    const token = localStorage.getItem(USER_TOKEN_KEY);
    // Best-effort server logout; ignore network errors (token is already client-side).
    try { userApi.post("/users/logout", undefined, { skipAuthRedirect: true, skipAuthRefresh: true, timeout: 15000, headers: token ? { Authorization: `Bearer ${token}` } : {} }).catch(() => { /* fire-and-forget */ }); }
    catch { /* userApi unavailable in test envs */ }
    localStorage.removeItem(USER_TOKEN_KEY);
    setUser(false);
  }, []);
  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem(USER_TOKEN_KEY);
    if (!token) return null;
    const generation = userAuthGenerationRef.current;
    const sessionVersion = getUserAuthSessionVersion();
    try {
      const { data } = await userApi.get("/users/me", { skipAuthRedirect: true, timeout: 15000 });
      if (
        !mountedRef.current
        || generation !== userAuthGenerationRef.current
        || !isUserAuthSessionCurrent(sessionVersion)
        || !localStorage.getItem(USER_TOKEN_KEY)
      ) return null;
      setUser(data);
      return data;
    } catch (error) {
      if (
        mountedRef.current
        && generation === userAuthGenerationRef.current
        && isUserAuthSessionCurrent(sessionVersion)
        && !error.authSuperseded
        && isConfirmedInvalidUserAuth(error)
      ) {
        localStorage.removeItem(USER_TOKEN_KEY);
        setUser(false);
      }
      return null;
    }
  }, []);
  const setUserBalance = useCallback((balance) => {
    setUser((u) => (u && typeof u === "object" ? { ...u, reading_seconds_balance: balance } : u));
  }, []);

  // Memoise the context value so consumers don't re-render on every parent render.
  const value = useMemo(() => ({
    admin, user,
    // backwards-compatible aliases (Admin pages used `login`/`logout`)
    login: adminLogin, logout: adminLogout,
    adminLogin, adminLogout,
    userSignup, userLogin, userLogout,
    refreshUser, setUserBalance,
  }), [admin, user, adminLogin, adminLogout, userSignup, userLogin, userLogout, refreshUser, setUserBalance]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
