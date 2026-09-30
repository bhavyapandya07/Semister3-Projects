import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    try { await signIn(email, password); navigate(location.state?.from?.pathname ?? "/", { replace: true }); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }
  return <section className="panel narrow"><h1>Sign in</h1><form onSubmit={submit}>
    <label>Email<input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
    <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
    <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    {error && <p className="error" role="alert">{error}</p>}
  </form><p>New student? <Link to="/register">Create an account</Link></p></section>;
}
