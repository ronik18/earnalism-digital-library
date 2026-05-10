import { useEffect, useState } from "react";
import { Link, useNavigate, Navigate, useSearchParams } from "react-router-dom";
import { useGoogleLogin } from "@react-oauth/google";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { API, USER_TOKEN_KEY, formatError } from "../lib/api";
import { toast } from "sonner";
import { Mail, Lock } from "lucide-react";
import useSEO from "../hooks/useSEO";
import BrandMark from "../components/BrandMark";

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || "";

export default function Login() {
  useSEO({
    title: "Sign In — The Earnalism Digital Library",
    description: "Sign in to your reading account at The Earnalism Digital Library.",
  });
  const { user, userLogin, refreshUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") || "/account";

  // ---------- Mobile OTP ----------
  const [mobile, setMobile] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [otpLoading, setOtpLoading] = useState(false);

  useEffect(() => {
    if (countdown <= 0) return;
    const id = setInterval(() => setCountdown((c) => Math.max(0, c - 1)), 1000);
    return () => clearInterval(id);
  }, [countdown]);

  const completeGoogle = async (credential) => {
    try {
      const { data } = await axios.post(`${API}/auth/google`, { credential });
      localStorage.setItem(USER_TOKEN_KEY, data.token);
      await refreshUser();
      toast.success("Welcome.");
      nav("/library", { replace: true });
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || "Google sign-in failed");
    }
  };

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

  const sendOtp = async () => {
    setOtpLoading(true);
    try {
      await axios.post(`${API}/auth/otp/request`, { mobile: `+91${mobile}` });
      setOtpSent(true);
      setCountdown(60);
      toast.success("OTP sent.");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || "Could not send OTP");
    } finally {
      setOtpLoading(false);
    }
  };

  const verifyOtp = async () => {
    setOtpLoading(true);
    try {
      const { data } = await axios.post(`${API}/auth/otp/verify`, { mobile: `+91${mobile}`, otp });
      localStorage.setItem(USER_TOKEN_KEY, data.token);
      await refreshUser();
      toast.success("Welcome.");
      nav("/library", { replace: true });
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || "Verification failed");
    } finally {
      setOtpLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-5 py-16" data-testid="user-login-page">
      <div className="card-elegant p-8 sm:p-12 w-full max-w-md">
        <Link to="/" className="block mb-6 leading-none" aria-label="The Earnalism Digital Library — Home"><BrandMark variant="auth" /></Link>
        <div className="italic-eyebrow mb-3">A quiet reading room</div>
        <h1 className="font-serif-light text-3xl sm:text-[2.4rem] text-burgundy leading-tight">Sign in to your <span className="italic-accent">library</span>.</h1>
        <div className="gold-rule-thin mt-5" />
        <p className="text-charcoal-soft mt-6 text-sm font-light leading-relaxed">
          Pick up where you left off. Your reading time and shelf travel with you.
        </p>

        {GOOGLE_CLIENT_ID && <GoogleSignInButton onComplete={completeGoogle} />}

        {GOOGLE_CLIENT_ID && (
          <div className="mt-6 flex items-center gap-3 text-[0.7rem] tracking-[0.22em] uppercase text-charcoal-soft/60">
            <div className="flex-1 h-px bg-current/20" />
            <span>or</span>
            <div className="flex-1 h-px bg-current/20" />
          </div>
        )}

        <div className="mt-6">
          <div
            className="flex items-stretch rounded-xl overflow-hidden"
            style={{ border: "1px solid #E8DDD8" }}
          >
            <span
              className="px-3 py-3"
              style={{
                background: "#F5F0E8",
                color: "#7A5C62",
                fontFamily: "Inter, sans-serif",
                fontSize: 14,
                borderRight: "1px solid #E8DDD8",
              }}
            >
              +91
            </span>
            <input
              type="tel"
              maxLength={10}
              placeholder="Mobile number"
              value={mobile}
              onChange={(e) => setMobile(e.target.value.replace(/\D/g, "").slice(0, 10))}
              className="flex-1 px-3 py-3"
              style={{
                background: "transparent",
                border: "none",
                outline: "none",
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 16,
              }}
              data-testid="login-mobile-input"
            />
            <button
              type="button"
              disabled={otpLoading || mobile.length < 10 || countdown > 0}
              onClick={sendOtp}
              className="px-4 py-3"
              style={{
                background: "#6B1020",
                color: "#FAF7F0",
                fontFamily: "Inter, sans-serif",
                fontSize: 13,
                opacity: otpLoading || mobile.length < 10 ? 0.5 : 1,
              }}
              data-testid="login-mobile-send"
            >
              {countdown > 0 ? `${countdown}s` : "Send OTP"}
            </button>
          </div>

          {otpSent && (
            <div className="mt-4">
              <input
                type="text"
                maxLength={6}
                inputMode="numeric"
                placeholder="______"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                className="block mx-auto"
                style={{
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  borderBottom: "2px solid #6B1020",
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 24,
                  textAlign: "center",
                  letterSpacing: "0.3em",
                  maxWidth: 200,
                  width: "100%",
                }}
                data-testid="login-mobile-otp-input"
              />
              <button
                type="button"
                disabled={otp.length < 6 || otpLoading}
                onClick={verifyOtp}
                className="w-full mt-4 rounded-xl py-3"
                style={{
                  background: "#6B1020",
                  color: "#FAF7F0",
                  fontFamily: "Inter, sans-serif",
                  fontSize: 15,
                  fontWeight: 500,
                  opacity: otp.length < 6 ? 0.5 : 1,
                }}
                data-testid="login-mobile-verify"
              >
                Verify & Login
              </button>
              <div className="mt-3 text-center">
                {countdown > 0 ? (
                  <span style={{ fontFamily: "Inter, sans-serif", fontSize: 12, color: "#A88A8F" }}>
                    Resend in {countdown}s
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={sendOtp}
                    style={{
                      fontFamily: "Inter, sans-serif",
                      fontSize: 12,
                      color: "#6B1020",
                      textDecoration: "underline",
                    }}
                  >
                    Resend OTP
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        <form onSubmit={submit} className="mt-6 space-y-4" data-testid="user-login-form">
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

        <p className="mt-8 text-sm text-charcoal-soft text-center font-light">
          New to The Earnalism? <Link to="/signup" className="text-burgundy underline decoration-[var(--brand-gold)]/60 underline-offset-4 hover:decoration-[var(--brand-gold)]" data-testid="link-to-signup">Create an account</Link>
        </p>
      </div>
    </div>
  );
}

function GoogleSignInButton({ onComplete }) {
  const googleLogin = useGoogleLogin({
    flow: "implicit",
    onSuccess: async (resp) => {
      const credential = resp?.credential || resp?.access_token;
      if (credential) return onComplete(credential);
      toast.error("Google sign-in failed");
    },
    onError: () => toast.error("Google sign-in failed"),
  });

  return (
    <button
      type="button"
      onClick={() => googleLogin()}
      className="mt-8 w-full flex items-center justify-center gap-3 rounded-xl px-4 py-3"
      style={{
        background: "white",
        border: "1px solid #6B1020",
        fontFamily: "'Crimson Pro', Georgia, serif",
        fontSize: 16,
        color: "#1C0A0E",
      }}
      data-testid="login-google"
    >
      <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
        <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.49h4.85a4.14 4.14 0 0 1-1.79 2.7v2.24h2.9c1.7-1.57 2.68-3.88 2.68-6.59z"/>
        <path fill="#34A853" d="M9 18c2.43 0 4.46-.8 5.95-2.18l-2.9-2.24c-.8.55-1.83.88-3.05.88-2.34 0-4.32-1.58-5.03-3.7H.96v2.32A8.99 8.99 0 0 0 9 18z"/>
        <path fill="#FBBC05" d="M3.97 10.76A5.4 5.4 0 0 1 3.68 9c0-.61.1-1.2.29-1.76V4.92H.96A8.99 8.99 0 0 0 0 9c0 1.45.35 2.83.96 4.08l3.01-2.32z"/>
        <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.43 1.34l2.57-2.57A8.99 8.99 0 0 0 9 0 8.99 8.99 0 0 0 .96 4.92l3.01 2.32C4.68 5.16 6.66 3.58 9 3.58z"/>
      </svg>
      Continue with Google
    </button>
  );
}
