import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { formatError } from "../lib/api";
import { toast } from "sonner";

export default function AdminLogin() {
  const { admin, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  if (admin) return <Navigate to="/admin" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(email, password);
      toast.success("Welcome back.");
      nav("/admin");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || "Login failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-5 py-16" data-testid="admin-login-page">
      <div className="card-elegant p-8 sm:p-12 w-full max-w-md">
        <div className="overline mb-3">The Earnalism</div>
        <h1 className="font-serif-display text-3xl text-burgundy">Admin sign in</h1>
        <p className="text-charcoal-soft mt-2 text-sm">Manage books, journal entries, and reader inquiries.</p>
        <form onSubmit={submit} className="mt-8 space-y-5">
          <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" className="input-elegant" data-testid="login-email" />
          <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" className="input-elegant" data-testid="login-password" />
          <button disabled={busy} className="btn-primary w-full disabled:opacity-60" data-testid="login-submit">{busy ? "Signing in…" : "Sign In"}</button>
        </form>
      </div>
    </div>
  );
}
