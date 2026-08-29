import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { userApi, formatMinutes } from "../lib/api";
import { toast } from "sonner";
import { LogOut, BookOpen, Clock, ArrowUpRight, MonitorSmartphone, ShieldCheck, Trash2 } from "lucide-react";
import useSEO from "../hooks/useSEO";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import { getReadingPassConfig, getReadingPassDevices, revokeReadingPassDevice } from "../lib/readingPassApi";
import ExperienceBottomNavigation from "../experiences-v2/shared/ExperienceBottomNavigation";
import "../styles/auth-account.css";

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

function AccountProfileMobile({ user, balance, activityCount, readingPassEnabled, onLogout, onNavigate }) {
  const initial = String(user.name || "Reader").trim().slice(0, 1).toUpperCase() || "R";
  return (
    <section className="account-profile-mobile" aria-labelledby="account-profile-mobile-title" data-testid="account-profile-mobile">
      <div className="account-profile-mobile__identity">
        <div className="account-profile-mobile__avatar" aria-hidden="true">{initial}</div>
        <h1 id="account-profile-mobile-title">My Profile</h1>
        <strong>{user.name || "Reader"}</strong>
        <span>{user.email}</span>
      </div>
      <nav className="account-profile-mobile__actions" aria-label="Account options">
        <Link to="/pricing" className="account-profile-mobile__row" data-testid="account-profile-mobile-pass"><Clock aria-hidden="true" /><span><b>Reading Pass</b><small>{formatMinutes(balance)} available</small></span><ArrowUpRight aria-hidden="true" /></Link>
        <a href="#account-transactions" className="account-profile-mobile__row"><BookOpen aria-hidden="true" /><span><b>Recent activity</b><small>{activityCount ? `${activityCount} recorded activities` : "Your reading will appear here"}</small></span><ArrowUpRight aria-hidden="true" /></a>
        {readingPassEnabled ? <a href="#reading-pass-devices" className="account-profile-mobile__row"><MonitorSmartphone aria-hidden="true" /><span><b>Signed-in devices</b><small>Manage active Reading Pass sessions</small></span><ArrowUpRight aria-hidden="true" /></a> : null}
        <Link to="/my-library" className="account-profile-mobile__row"><BookOpen aria-hidden="true" /><span><b>My Library</b><small>Open saved editions and reading activity</small></span><ArrowUpRight aria-hidden="true" /></Link>
        <button type="button" className="account-profile-mobile__row account-profile-mobile__signout" onClick={onLogout} data-testid="account-profile-mobile-logout"><LogOut aria-hidden="true" /><span><b>Sign out</b><small>End this signed-in session</small></span></button>
      </nav>
      <ExperienceBottomNavigation active="profile" onNavigate={onNavigate} />
    </section>
  );
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
  const [readingPassEnabled, setReadingPassEnabled] = useState(false);
  const [devices, setDevices] = useState([]);
  const [devicesLoading, setDevicesLoading] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    if (!user) return;
    refreshUser();
    userApi.get("/users/me/transactions")
      .then((r) => setTxs(r.data || []))
      .catch(() => setTxs([]))
      .finally(() => setLoading(false));
  }, [user, refreshUser]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    getReadingPassConfig()
      .then((config) => {
        if (cancelled || !config?.enabled) return;
        setReadingPassEnabled(true);
        setDevicesLoading(true);
        getReadingPassDevices()
          .then((rows) => {
            if (!cancelled) setDevices(rows);
          })
          .catch(() => {
            if (!cancelled) setDevices([]);
          })
          .finally(() => {
            if (!cancelled) setDevicesLoading(false);
          });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [user]);

  if (user === null) return <div className="py-32 text-center text-charcoal-soft" role="status" aria-live="polite">Loading your reading account…</div>;
  if (!user) return <Navigate to="/login?next=/account" replace />;

  const balance = Number(user.reading_seconds_balance || 0);
  const activityRows = aggregateActivity(txs);
  const onLogout = () => {
    userLogout();
    toast.success("Signed out.");
    nav("/", { replace: true });
  };
  const onProfileNavigate = (target) => {
    const destinations = { home: "/", library: "/library", passes: "/pricing", profile: "/account" };
    nav(destinations[target] || "/account");
  };
  const revokeDevice = async (device) => {
    const target = device.session_id || device.device_id;
    if (!target || !window.confirm(`Revoke ${device.device_label || "this device"}? Any active Reading Pass lease there will stop.`)) return;
    try {
      await revokeReadingPassDevice(target);
      setDevices((rows) => rows.map((row) => (
        (row.session_id || row.device_id) === target
          ? { ...row, status: "revoked", revoked_at: new Date().toISOString() }
          : row
      )));
      toast.success(device.current ? "This device was revoked. Sign in again to continue." : "Device access revoked.");
      if (device.current) {
        userLogout();
        nav("/login?next=/account", { replace: true });
      }
    } catch {
      toast.error("The device could not be revoked. Please try again.");
    }
  };

  return (
    <div className="account-page-modern min-h-[70vh] px-5 sm:px-8 lg:px-12 py-12 sm:py-16" data-testid="account-page">
      <AccountProfileMobile user={user} balance={balance} activityCount={activityRows.length} readingPassEnabled={readingPassEnabled} onLogout={onLogout} onNavigate={onProfileNavigate} />
      <div className="max-w-4xl mx-auto">
        <div className="account-hero mb-8 sm:mb-10">
          <div className="account-hero-summary">
            <div className="italic-eyebrow">Your account</div>
            <h1 className="font-serif-light text-4xl sm:text-5xl text-burgundy leading-tight mt-2">
              Welcome, <span className="italic-accent">{user.name?.split(" ")[0] || "Reader"}</span>.
            </h1>
            <p className="account-hero-email text-sm text-charcoal-soft mt-2 font-light">{user.email}</p>
          </div>
          <button onClick={onLogout} className="btn-secondary" data-testid="account-logout">
            <LogOut size={14} className="mr-2" /> Sign out
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-12">
          <div className="account-panel account-balance-panel p-7 sm:p-8" data-testid="account-balance-card" role="region" aria-labelledby="account-balance-heading">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80">
              <Clock size={13} strokeWidth={1.5} /> Reading time
            </div>
            <h2 id="account-balance-heading" className="account-balance-value font-serif-display text-5xl sm:text-6xl text-burgundy mt-4 leading-none" data-testid="account-balance">
              {formatMinutes(balance)}
            </h2>
            <div className="gold-rule-thin mt-4" />
            <p className="text-charcoal-soft text-sm font-light mt-5 leading-relaxed">
              {readingPassEnabled
                ? "Reading Pass uses short server leases and a 10-second heartbeat. Reading bills only while protected text is active; listening bills only while approved audio is playing."
                : "Reading is billed in 30-second pulses only while a chapter is open, visible, and active. Hidden tabs, sleeping devices, and long idle gaps are not charged."}
            </p>
            <p className="mt-3 text-xs leading-relaxed text-charcoal-soft/80" data-testid="account-wallet-explainer">
              Read the first 3 pages free. Listening requires an active Reading Pass.
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

          <div className="account-panel account-continue-panel p-7 sm:p-8 flex flex-col">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80">
              <BookOpen size={13} strokeWidth={1.5} /> Continue reading
            </div>
            <p className="font-serif-display text-xl text-charcoal mt-4 leading-snug">
              Return to a book from the live shelf. Your time begins only when the words do.
            </p>
            <div className="mt-auto pt-6">
              <Link
                to="/reader/dracula"
                className="btn-primary w-full sm:w-auto"
                data-testid="account-go-library"
                onClick={() => trackFunnelEvent("return_resume_reading_click", {
                  source: "account_continue_reading",
                  book_slug: "dracula",
                })}
              >
                Continue reading
              </Link>
            </div>
          </div>
        </div>

        {readingPassEnabled && (
          <section className="account-panel p-6 sm:p-8 mb-12" aria-labelledby="reading-pass-devices-heading" data-testid="reading-pass-devices">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-2 italic-eyebrow opacity-80">
                  <MonitorSmartphone size={14} strokeWidth={1.5} /> Signed-in devices
                </div>
                <h2 id="reading-pass-devices-heading" className="font-serif-display text-2xl text-burgundy mt-3">Reading Pass sessions</h2>
                <p className="text-sm text-charcoal-soft mt-2 max-w-2xl">Several devices may stay signed in, but only one may consume Reading Pass time. Revoking a device immediately invalidates its active lease.</p>
              </div>
              <ShieldCheck size={24} className="text-burgundy" aria-hidden="true" />
            </div>
            <div className="gold-rule-thin mt-5 mb-4" />
            {devicesLoading ? (
              <p className="text-sm text-charcoal-soft" role="status" aria-live="polite">Loading signed-in devices…</p>
            ) : devices.length === 0 ? (
              <p className="text-sm text-charcoal-soft">No Reading Pass device sessions are registered yet.</p>
            ) : (
              <ul className="grid gap-3">
                {devices.map((device) => {
                  const revoked = device.status !== "active";
                  return (
                    <li key={device.session_id || device.device_id} className="account-device-row flex items-center justify-between gap-4 rounded-xl border px-4 py-3">
                      <div className="min-w-0">
                        <strong className="block text-sm text-charcoal truncate">{device.device_label || "Browser"}{device.current ? " · This device" : ""}</strong>
                        <span className="block text-xs text-charcoal-soft mt-1">{revoked ? "Revoked" : "Active"}{device.last_seen_at ? ` · Last seen ${new Date(device.last_seen_at).toLocaleString()}` : ""}</span>
                      </div>
                      {!revoked && (
                        <button type="button" onClick={() => revokeDevice(device)} className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-full border border-brand text-burgundy hover:bg-brand-ivory" aria-label={`Revoke ${device.device_label || "device"}`}>
                          <Trash2 size={16} aria-hidden="true" />
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        )}

        <div className="account-panel p-6 sm:p-8 overflow-x-auto" data-testid="account-transactions">
          <h2 className="font-serif-display text-2xl text-burgundy">Recent activity</h2>
          <div className="gold-rule-thin mt-3 mb-5" />
          {loading ? (
            <p className="text-charcoal-soft text-sm" role="status" aria-live="polite">Loading recent reading activity…</p>
          ) : activityRows.length === 0 ? (
            <p className="text-charcoal-soft text-sm font-light" role="status">No reading activity yet. Open a book from the library to begin.</p>
          ) : (
            <table className="account-activity-table w-full text-sm">
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
