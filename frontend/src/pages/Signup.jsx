import { useState } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { formatError } from "../lib/api";
import { toast } from "sonner";
import { User, Mail, Lock } from "lucide-react";
import useSEO from "../hooks/useSEO";
import AuthPageShell from "../components/AuthPageShell";

export default function Signup() {
  useSEO({
    title: "Create an Account — The Earnalism Digital Library",
    description: "Create your reading account at The Earnalism Digital Library — a quiet, curated reading room.",
    robots: "noindex, nofollow",
  });
  const { user, userSignup } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  if (user === null) return <div className="py-32 text-center text-charcoal-soft" role="status" aria-live="polite">Loading account setup…</div>;
  if (user) return <Navigate to="/account" replace />;

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      await userSignup(name, email, password);
      toast.success("Welcome to The Earnalism.");
      nav("/account", { replace: true });
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || "Sign-up failed");
    } finally { setBusy(false); }
  };

  return (
    <AuthPageShell
      eyebrow="Open a reading account"
      title={<>A library that <span className="italic-accent">remembers</span> you.</>}
      introduction="Keep your reading balance, activity, and approved library access in one calm place."
      testId="user-signup-page"
      footer={<p className="mt-8 text-center text-sm font-light text-charcoal-soft">Already a reader? <Link to="/login" className="inline-flex min-h-11 items-center text-burgundy underline decoration-[var(--brand-gold)]/60 underline-offset-4 hover:decoration-[var(--brand-gold)]" data-testid="link-to-login">Sign in</Link></p>}
    >
        <div className="auth-account-note mt-5 rounded-xl border px-4 py-3 text-xs leading-relaxed text-charcoal-soft" data-testid="signup-wallet-note">
          Read the first 3 pages free. Listening requires an active Reading Pass.
        </div>

        <form onSubmit={submit} className="auth-account-form mt-8 space-y-4" data-testid="user-signup-form" aria-describedby="signup-wallet-help">
          <p id="signup-wallet-help" className="sr-only">
            Create an account to manage your Reading Pass and return to your place across eligible books.
          </p>
          <label className="block">
            <span className="overline block mb-2">Your name</span>
            <div className="relative">
              <User size={15} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft/60" />
              <input required type="text" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Sample Reader" className="input-elegant pl-9" data-testid="user-signup-name" />
            </div>
          </label>
          <label className="block">
            <span className="overline block mb-2">Email</span>
            <div className="relative">
              <Mail size={15} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft/60" />
              <input required type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="input-elegant pl-9" data-testid="user-signup-email" />
            </div>
          </label>
          <label className="block">
            <span className="overline block mb-2">Password · min 8 chars</span>
            <div className="relative">
              <Lock size={15} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-charcoal-soft/60" />
              <input required type="password" minLength={8} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Choose a quiet password" className="input-elegant pl-9" data-testid="user-signup-password" />
            </div>
          </label>
          <button disabled={busy} className="btn-primary w-full disabled:opacity-60" data-testid="user-signup-submit">
            {busy ? "Creating account…" : "Create Account"}
          </button>
        </form>

    </AuthPageShell>
  );
}
