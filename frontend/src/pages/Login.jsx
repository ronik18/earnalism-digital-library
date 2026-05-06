import { useState } from "react";
import { Link, useNavigate, Navigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { formatError } from "../lib/api";
import { toast } from "sonner";
import { Mail, Lock } from "lucide-react";
import useSEO from "../hooks/useSEO";

export default function Login() {
  useSEO({
    title: "Sign In — The Earnalism Digital Library",
    description: "Sign in to your reading account at The Earnalism Digital Library.",
  });
  const { user, userLogin } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") || "/account";

  if (user === null) return <div className="py-32 text-center text-charcoal-soft">Loading…</div>;
  if (user) return <Navigate to={next} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await userLogin(email, password);
      toast.success("Welcome back.");
      nav(next, { replace: true });
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || "Sign-in failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-5 py-16" data-testid="user-login-page">
      <div className="card-elegant p-8 sm:p-12 w-full max-w-md">
        <div className="italic-eyebrow mb-3">A quiet reading room</div>
        <h1 className="font-serif-light text-3xl sm:text-[2.4rem] text-burgundy leading-tight">Sign in to your <span className="italic-accent">library</span>.</h1>
        <div className="gold-rule-thin mt-5" />
        <p className="text-charcoal-soft mt-6 text-sm font-light leading-relaxed">
          Pick up where you left off. Your reading time and shelf travel with you.
        </p>

        <form onSubmit={submit} className="mt-8 space-y-4" data-testid="user-login-form">
          <label className="block">
            <span className="overline block mb-2">Email</span>
            <div className="relative">
              <Mail size={15} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft/60" />
              <input required type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="input-elegant pl-9" data-testid="user-login-email" />
            </div>
          </label>
          <label className="block">
            <span className="overline block mb-2">Password</span>
            <div className="relative">
              <Lock size={15} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft/60" />
              <input required type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="input-elegant pl-9" data-testid="user-login-password" />
            </div>
          </label>
          <button disabled={busy} className="btn-primary w-full disabled:opacity-60" data-testid="user-login-submit">
            {busy ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <div className="mt-6 flex items-center gap-3 text-[0.7rem] tracking-[0.22em] uppercase text-charcoal-soft/60">
          <div className="flex-1 h-px bg-current/20" />
          <span>or</span>
          <div className="flex-1 h-px bg-current/20" />
        </div>

        <div className="mt-6 space-y-3" data-testid="user-login-mock-providers">
          <button type="button" disabled title="Coming soon" className="btn-secondary w-full opacity-40 cursor-not-allowed" data-testid="login-google">
            Continue with Google · Coming soon
          </button>
          <button type="button" disabled title="Coming soon" className="btn-secondary w-full opacity-40 cursor-not-allowed" data-testid="login-mobile">
            Continue with Mobile OTP · Coming soon
          </button>
        </div>

        <p className="mt-8 text-sm text-charcoal-soft text-center font-light">
          New to The Earnalism? <Link to="/signup" className="text-burgundy underline decoration-[var(--brand-gold)]/60 underline-offset-4 hover:decoration-[var(--brand-gold)]" data-testid="link-to-signup">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
