import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { userApi, formatMinutes } from "../lib/api";
import { toast } from "sonner";
import { LogOut, BookOpen, Clock, ArrowUpRight } from "lucide-react";
import useSEO from "../hooks/useSEO";

export default function Account() {
  useSEO({
    title: "Your Account — The Earnalism Digital Library",
    description: "Manage your reading-time wallet and recent activity at The Earnalism.",
  });
  const { user, userLogout, refreshUser } = useAuth();
  const [txs, setTxs] = useState([]);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    if (!user) return;
    refreshUser();
    userApi.get("/users/me/transactions")
      .then((r) => setTxs(r.data || []))
      .catch(() => setTxs([]))
      .finally(() => setLoading(false));
  }, [user, refreshUser]);

  if (user === null) return <div className="py-32 text-center text-charcoal-soft">Loading…</div>;
  if (!user) return <Navigate to="/login?next=/account" replace />;

  const balance = Number(user.reading_seconds_balance || 0);
  const onLogout = () => {
    userLogout();
    toast.success("Signed out.");
    nav("/", { replace: true });
  };

  return (
    <div className="min-h-[70vh] px-5 sm:px-8 lg:px-12 py-14 sm:py-20" data-testid="account-page">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-10">
          <div>
            <div className="italic-eyebrow">Your account</div>
            <h1 className="font-serif-light text-4xl sm:text-5xl text-burgundy leading-tight mt-2">
              Welcome, <span className="italic-accent">{user.name?.split(" ")[0] || "Reader"}</span>.
            </h1>
            <p className="text-sm text-charcoal-soft mt-1 font-light">{user.email}</p>
          </div>
          <button onClick={onLogout} className="btn-secondary" data-testid="account-logout">
            <LogOut size={14} className="mr-2" /> Sign out
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-12">
          <div className="card-elegant p-7 sm:p-8" data-testid="account-balance-card">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80">
              <Clock size={13} strokeWidth={1.5} /> Reading time
            </div>
            <div className="font-serif-display text-5xl sm:text-6xl text-burgundy mt-4 leading-none" data-testid="account-balance">
              {formatMinutes(balance)}
            </div>
            <div className="gold-rule-thin mt-4" />
            <p className="text-charcoal-soft text-sm font-light mt-5 leading-relaxed">
              Reading is billed in 30-second pulses while a chapter is open and visible. The first chapter of every book is on the house.
            </p>
            <Link to="/pricing" className="inline-flex items-center gap-2 text-[0.72rem] tracking-[0.22em] uppercase text-burgundy mt-6 hover:opacity-70" data-testid="account-buy-time">
              Buy reading time <ArrowUpRight size={13} strokeWidth={1.5} />
            </Link>
          </div>

          <div className="card-elegant p-7 sm:p-8 flex flex-col">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80">
              <BookOpen size={13} strokeWidth={1.5} /> Continue reading
            </div>
            <p className="font-serif-display text-xl text-charcoal mt-4 leading-snug">
              Visit the library and choose a title — your time begins only when the words do.
            </p>
            <div className="mt-auto pt-6">
              <Link to="/library" className="btn-primary w-full sm:w-auto" data-testid="account-go-library">Open the Library</Link>
            </div>
          </div>
        </div>

        <div className="card-elegant p-6 sm:p-8 overflow-x-auto" data-testid="account-transactions">
          <h2 className="font-serif-display text-2xl text-burgundy">Recent activity</h2>
          <div className="gold-rule-thin mt-3 mb-5" />
          {loading ? (
            <p className="text-charcoal-soft text-sm">Loading…</p>
          ) : txs.length === 0 ? (
            <p className="text-charcoal-soft text-sm font-light">No reading activity yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-charcoal-soft border-b border-brand">
                  <th className="py-3 pr-4">When</th>
                  <th className="py-3 pr-4">Type</th>
                  <th className="py-3 pr-4">Time</th>
                  <th className="py-3 pr-4">Reason</th>
                </tr>
              </thead>
              <tbody>
                {txs.map((t) => (
                  <tr key={t.id} className="border-b border-brand/60" data-testid={`tx-row-${t.id}`}>
                    <td className="py-3 pr-4 align-top text-charcoal-soft whitespace-nowrap">{new Date(t.created_at).toLocaleString()}</td>
                    <td className="py-3 pr-4 align-top">
                      <span className={`text-[0.7rem] tracking-[0.18em] uppercase ${t.type === "credit" ? "text-emerald-700" : t.type === "debit" ? "text-rose-700" : "text-charcoal-soft"}`}>{t.type}</span>
                    </td>
                    <td className={`py-3 pr-4 align-top font-serif-display text-base ${t.seconds < 0 ? "text-rose-700" : "text-emerald-700"}`}>
                      {t.seconds >= 0 ? "+" : "−"}{formatMinutes(Math.abs(t.seconds))}
                    </td>
                    <td className="py-3 pr-4 align-top text-charcoal-soft">{t.reason || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
