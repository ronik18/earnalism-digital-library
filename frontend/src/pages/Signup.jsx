import { useState } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { formatError } from "../lib/api";
import { toast } from "sonner";
import { User, Mail, Lock } from "lucide-react";
import useSEO from "../hooks/useSEO";
import BrandMark from "../components/BrandMark";

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

  if (user === null) return <div className="py-32 text-center text-charcoal-soft">Loading…</div>;
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
    <div className="min-h-[80vh] flex items-center justify-center px-5 py-16" data-testid="user-signup-page">
      <div className="card-elegant p-8 sm:p-12 w-full max-w-md">
        <Link to="/" className="block mb-6 leading-none" aria-label="The Earnalism Digital Library — Home"><BrandMark variant="auth" /></Link>
        <div className="italic-eyebrow mb-3">Open a reading account</div>
        <h1 className="font-serif-light text-3xl sm:text-[2.4rem] text-burgundy leading-tight">A library that <span className="italic-accent">remembers</span> you.</h1>
        <div className="gold-rule-thin mt-5" />
        <p className="text-charcoal-soft mt-6 text-sm font-light leading-relaxed">
          Create a quiet account for Dracula, your reading-time wallet, and future classics that pass the rights-safe pipeline.
        </p>
        <div className="mt-5 rounded-md border border-brand-soft bg-white/55 px-4 py-3 text-xs leading-relaxed text-charcoal-soft" data-testid="signup-wallet-note">
          Chapter 1 is free. Reading time is added only when you choose a pass, and there is no subscription or autorenewal.
        </div>

        <form onSubmit={submit} className="mt-8 space-y-4" data-testid="user-signup-form">
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

        <p className="mt-8 text-sm text-charcoal-soft text-center font-light">
          Already a reader? <Link to="/login" className="text-burgundy underline decoration-[var(--brand-gold)]/60 underline-offset-4 hover:decoration-[var(--brand-gold)]" data-testid="link-to-login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
