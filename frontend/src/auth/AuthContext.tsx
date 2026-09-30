import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { SessionUser } from "@srms/shared";
import { api, setAccessToken } from "../api/client";

interface AuthValue { user: SessionUser | null; ready: boolean; signIn(email: string, password: string): Promise<void>; signOut(): Promise<void>; }
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let live = true;
    const expireSession = () => setUser(null);
    window.addEventListener("srms:logout", expireSession);
    api.restoreSession()
      .then((data) => { if (live) { setAccessToken(data.token); setUser(data.user); } })
      .catch(() => setAccessToken(null)).finally(() => { if (live) setReady(true); });
    return () => { live = false; window.removeEventListener("srms:logout", expireSession); };
  }, []);
  async function signIn(email: string, password: string) {
    const session = await api.login(email, password);
    setAccessToken(session.token);
    setUser(session.user);
  }
  async function signOut() {
    try { await api.logout(); } finally { setAccessToken(null); setUser(null); }
  }
  const value = useMemo(() => ({ user, ready, signIn, signOut }), [user, ready]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
