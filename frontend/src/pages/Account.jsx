import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { userApi, formatMinutes } from "../lib/api";
import { toast } from "sonner";
import { LogOut, BookOpen, Clock, ArrowUpRight } from "lucide-react";
import useSEO from "../hooks/useSEO";
import { trackFunnelEvent } from "../lib/funnelAnalytics";

const FALLBACK_SESSION_GAP_MS = 15 * 60 * 1000;

function txDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? new Date(0) : date;
}

function readingReasonLabel(reason = "") {
  const title = String(reason || "").replace(/^Reading\s+/i, "").trim();
  return title ? `Reading session - ${title}` : "Reading session";
}

function appendConsume(group, tx) {
  const at = txDate(tx.created_at);
  group.seconds += Number(tx.seconds || 0);
  group.count += 1;
  if (at < group.startAt) group.startAt = at;
  if (at > group.endAt) {
    group.endAt = at;
    group.created_at = tx.created_at;
  }
}

function aggregateActivity(transactions = []) {
  const sorted = [...transactions].sort((a, b) => txDate(a.created_at) - txDate(b.created_at));
  const sessionGroups = new Map();
  const rows = [];
  let fallbackGroup = null;

  sorted.forEach((tx) => {
    if (tx.type !== "consume") {
      rows.push({
        ...tx,
        startAt: txDate(tx.created_at),
        endAt: txDate(tx.created_at),
        count: 1,
      });
      fallbackGroup = null;
      return;
    }

    const sessionId = tx.session_id || "";
    if (sessionId) {
      const key = `reading:${sessionId}`;
      let group = sessionGroups.get(key);
      if (!group) {
        const at = txDate(tx.created_at);
        group = {
          ...tx,
          id: key,
          reason: readingReasonLabel(tx.reason),
          seconds: 0,
          startAt: at,
          endAt: at,
          count: 0,
          source_ids: [],
        };
        sessionGroups.set(key, group);
        rows.push(group);
      }
      group.source_ids.push(tx.id);
      appendConsume(group, tx);
      fallbackGroup = null;
      return;
    }

    const at = txDate(tx.created_at);
    const canFoldIntoFallback = fallbackGroup
      && fallbackGroup.raw_reason === tx.reason
      && at - fallbackGroup.endAt <= FALLBACK_SESSION_GAP_MS;
    if (!canFoldIntoFallback) {
      fallbackGroup = {
        ...tx,
        id: `reading:${tx.id}`,
        reason: readingReasonLabel(tx.reason),
        raw_reason: tx.reason,
        seconds: 0,
        startAt: at,
        endAt: at,
        count: 0,
        source_ids: [],
      };
      rows.push(fallbackGroup);
    }
    fallbackGroup.source_ids.push(tx.id);
    appendConsume(fallbackGroup, tx);
  });

  return rows.sort((a, b) => b.endAt - a.endAt);
}

function formatActivityWhen(row) {
  const start = row.startAt || txDate(row.created_at);
  const end = row.endAt || txDate(row.created_at);
  if (Math.abs(end - start) < 60 * 1000) {
    return end.toLocaleString();
  }
  const sameDay = start.toDateString() === end.toDateString();
  if (sameDay) {
    return `${start.toLocaleDateString()}, ${start.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} - ${end.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
  }
  return `${start.toLocaleString()} - ${end.toLocaleString()}`;
}

export default function Account() {
  useSEO({
    title: "Your Account — The Earnalism Digital Library",
    description: "Manage your reading-time wallet and recent activity at The Earnalism.",
    robots: "noindex, nofollow",
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

  if (user === null) return <div className="py-32 text-center text-charcoal-soft" role="status" aria-live="polite">Loading your reading account…</div>;
  if (!user) return <Navigate to="/login?next=/account" replace />;

  const balance = Number(user.reading_seconds_balance || 0);
  const activityRows = aggregateActivity(txs);
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
          <div className="card-elegant p-7 sm:p-8" data-testid="account-balance-card" role="region" aria-labelledby="account-balance-heading">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80">
              <Clock size={13} strokeWidth={1.5} /> Reading time
            </div>
            <h2 id="account-balance-heading" className="font-serif-display text-5xl sm:text-6xl text-burgundy mt-4 leading-none" data-testid="account-balance">
              {formatMinutes(balance)}
            </h2>
            <div className="gold-rule-thin mt-4" />
            <p className="text-charcoal-soft text-sm font-light mt-5 leading-relaxed">
              Reading is billed in 30-second pulses only while a chapter is open, visible, and active. Hidden tabs, sleeping devices, and long idle gaps are not charged.
            </p>
            <p className="mt-3 text-xs leading-relaxed text-charcoal-soft/80" data-testid="account-wallet-explainer">
              Use this wallet to continue Dracula after the free preview. Future titles remain locked until their own approval gates pass.
            </p>
            <Link
              to="/pricing"
              className="inline-flex items-center gap-2 text-[0.72rem] tracking-[0.22em] uppercase text-burgundy mt-6 hover:opacity-70"
              data-testid="account-buy-time"
              onClick={() => trackFunnelEvent("pricing_page_view", {
                source: "account_wallet",
                book_slug: "dracula",
              })}
            >
              Add reading time <ArrowUpRight size={13} strokeWidth={1.5} />
            </Link>
          </div>

          <div className="card-elegant p-7 sm:p-8 flex flex-col">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80">
              <BookOpen size={13} strokeWidth={1.5} /> Continue reading
            </div>
            <p className="font-serif-display text-xl text-charcoal mt-4 leading-snug">
              Continue Dracula from the live shelf. Your time begins only when the words do.
            </p>
            <div className="mt-auto pt-6">
              <Link
                to="/library"
                className="btn-primary w-full sm:w-auto"
                data-testid="account-go-library"
                onClick={() => trackFunnelEvent("return_resume_reading_click", {
                  source: "account_continue_reading",
                  book_slug: "dracula",
                })}
              >
                Open Dracula Shelf
              </Link>
            </div>
          </div>
        </div>

        <div className="card-elegant p-6 sm:p-8 overflow-x-auto" data-testid="account-transactions">
          <h2 className="font-serif-display text-2xl text-burgundy">Recent activity</h2>
          <div className="gold-rule-thin mt-3 mb-5" />
          {loading ? (
            <p className="text-charcoal-soft text-sm" role="status" aria-live="polite">Loading recent reading activity…</p>
          ) : activityRows.length === 0 ? (
            <p className="text-charcoal-soft text-sm font-light" role="status">No reading activity yet. Open Dracula from the library to begin.</p>
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
                {activityRows.map((t) => (
                  <tr key={t.id} className="border-b border-brand/60" data-testid={`tx-row-${t.id}`}>
                    <td className="py-3 pr-4 align-top text-charcoal-soft whitespace-nowrap">{formatActivityWhen(t)}</td>
                    <td className="py-3 pr-4 align-top">
                      <span className={`text-[0.7rem] tracking-[0.18em] uppercase ${t.type === "credit" ? "text-emerald-700" : t.type === "debit" ? "text-rose-700" : "text-charcoal-soft"}`}>{t.type}</span>
                    </td>
                    <td className={`py-3 pr-4 align-top font-serif-display text-base ${t.seconds < 0 ? "text-rose-700" : "text-emerald-700"}`}>
                      {t.seconds >= 0 ? "+" : "−"}{formatMinutes(Math.abs(t.seconds))}
                    </td>
                    <td className="py-3 pr-4 align-top text-charcoal-soft">
                      {t.reason || "—"}
                      {t.type === "consume" && t.count > 1 && (
                        <span className="block text-xs text-charcoal-soft/70 mt-1">{t.count} billing pulses grouped</span>
                      )}
                    </td>
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
