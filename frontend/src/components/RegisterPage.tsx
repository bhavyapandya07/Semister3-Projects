import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";

export function RegisterPage() {
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [rollNumber, setRollNumber] = useState("");
  const [message, setMessage] = useState(""); const [error, setError] = useState(""); const navigate = useNavigate();
  async function submit(event: FormEvent) { event.preventDefault(); setError(""); setMessage("");
    if (password.length < 12) { setError("Use at least 12 characters for your password."); return; }
    try { await api.register({ name, email, password, rollNumber }); setMessage("Account created. You can sign in now."); setTimeout(() => navigate("/login"), 800); }
    catch (err) { setError((err as Error).message); }
  }
  return <section className="panel narrow"><h1>Student registration</h1><form onSubmit={submit}>
    <label>Name<input required minLength={2} value={name} onChange={(e) => setName(e.target.value)} /></label>
    <label>Email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
    <label>Student roll number<input required value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} /></label>
    <label>Password<input type="password" required minLength={12} value={password} onChange={(e) => setPassword(e.target.value)} /><small>At least 12 characters</small></label>
    <button>Create account</button>{error && <p className="error" role="alert">{error}</p>}{message && <p className="success">{message}</p>}
  </form><Link to="/login">Back to sign in</Link></section>;
}
