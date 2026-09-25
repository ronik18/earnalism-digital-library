import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { userApi, formatMinutes } from "../lib/api";
import { toast } from "sonner";
import { LogOut, BookOpen, Clock, ArrowUpRight, MonitorSmartphone, ShieldCheck, Trash2 } from "lucide-react";
import useSEO from "../hooks/useSEO";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
import { getReadingPassConfig, getReadingPassDevices, revokeReadingPassDevice } from "../lib/readingPassApi";
import { formatSessionDeviceLabel, formatSessionLastActive, sortSessionDevices } from "../lib/accountPresentation";
import ExperienceBottomNavigation from "../experiences-v2/shared/ExperienceBottomNavigation";
import { PUBLIC_PAID_COMMERCE_ENABLED } from "../lib/controlledLaunch";
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

function AccountVisualFixture() {
  const user = { name: "Review Reader", email: "review@example.invalid" };
  const devices = [
    {
      session_id: "visual-current-session",
      status: "active",
      current: true,
      device_label: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
      last_seen_at: "2026-09-24T06:00:00Z",
    },
    {
      session_id: "visual-previous-session",
      status: "revoked",
      current: false,
      device_label: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
      last_seen_at: "2026-09-16T09:54:00Z",
    },
  ];
  return (
    <div className="account-page-modern account-page-modern--visual-fixture min-h-[70vh] px-5 sm:px-8 lg:px-12 py-12 sm:py-16" data-testid="account-visual-fixture">
      <section className="account-content-container account-visual-fixture__desktop max-w-7xl mx-auto" aria-labelledby="account-visual-fixture-title">
        <div className="account-hero">
          <div className="account-hero-summary">
            <div className="italic-eyebrow">Your account</div>
            <h1 id="account-visual-fixture-title" className="font-serif-light text-4xl sm:text-5xl text-burgundy leading-tight mt-2">
              Welcome, <span className="italic-accent">Review</span>.
            </h1>
            <p className="account-hero-email text-sm text-charcoal-soft mt-2 font-light">{user.email}</p>
          </div>
          <button type="button" className="btn-secondary" data-testid="account-visual-fixture-signout"><LogOut size={14} className="mr-2" /> Sign out</button>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <section className="account-panel account-balance-panel p-7 sm:p-8" aria-labelledby="account-visual-fixture-balance">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80"><Clock size={13} strokeWidth={1.5} /> Reading Pass</div>
            <h2 id="account-visual-fixture-balance" className="account-balance-value font-serif-display text-3xl sm:text-4xl text-burgundy mt-4 leading-tight">Remaining balance: 0 minutes</h2>
            <div className="gold-rule-thin mt-4" />
            <p className="text-charcoal-soft text-sm font-light mt-5 leading-relaxed">The first 3 pages are free where a preview is available. A valid Reading Pass is required from page 4. Pass purchases are not available yet.</p>
            <div className="account-reading-pass-status mt-5 border-t border-brand/30 pt-4"><span className="block text-xs font-semibold uppercase tracking-[0.14em] text-burgundy">Reading Pass</span><span className="block mt-1 text-sm text-charcoal-soft">Purchases are not available yet. Your balance remains available for eligible reading.</span></div>
          </section>
          <section className="account-panel account-continue-panel p-7 sm:p-8 flex flex-col" aria-labelledby="account-visual-fixture-library">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80"><BookOpen size={13} strokeWidth={1.5} /> My Library</div>
            <h2 id="account-visual-fixture-library" className="font-serif-display text-xl text-charcoal mt-4 leading-snug">Your saved library is currently empty.</h2>
            <p className="text-sm mt-3">Explore the public catalog to begin a reading list.</p>
            <div className="mt-auto pt-6"><Link to="/library" className="btn-primary w-full sm:w-auto">Browse Library</Link></div>
          </section>
        </div>
        <section className="account-panel p-6 sm:p-8 mb-8" aria-labelledby="account-visual-fixture-sessions">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2 italic-eyebrow opacity-80"><MonitorSmartphone size={14} strokeWidth={1.5} /> Signed-in devices</div>
              <h2 id="account-visual-fixture-sessions" className="font-serif-display text-2xl text-burgundy mt-3">Reading Pass sessions</h2>
            </div>
            <ShieldCheck size={24} className="text-burgundy" aria-hidden="true" />
          </div>
          <div className="gold-rule-thin mt-5 mb-4" />
          <SessionGroups devices={devices} onRevoke={() => {}} />
        </section>
        <section className="account-panel p-6 sm:p-8" aria-labelledby="account-visual-fixture-activity">
          <h2 id="account-visual-fixture-activity" className="font-serif-display text-2xl text-burgundy">Recent activity</h2>
          <div className="gold-rule-thin mt-3 mb-5" />
          <p className="text-charcoal-soft text-sm font-light">No reading activity is recorded in this sanitized visual fixture.</p>
        </section>
      </section>
      <div className="account-mobile-navigation"><ExperienceBottomNavigation active="profile" onNavigate={() => {}} /></div>
    </div>
  );
}

export default function Account() {
  useSEO({
    title: "Your Account — The Earnalism Digital Library",
    description: "Manage your reading-time wallet and recent activity at The Earnalism.",
    robots: "noindex, nofollow",
  });
  const { user, userLogout, refreshUser } = useAuth();
  const location = useLocation();
  const visualFixture = process.env.REACT_APP_ENABLE_VISUAL_FIXTURES === "1" && new URLSearchParams(location.search).get("visual-fixture") === "1";
  const [txs, setTxs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [readingPassEnabled, setReadingPassEnabled] = useState(false);
  const [devices, setDevices] = useState([]);
  const [devicesLoading, setDevicesLoading] = useState(false);
  const nav = useNavigate();
  const userId = user && typeof user === "object" ? user.id : null;

  useEffect(() => {
    if (!userId) return undefined;
    let cancelled = false;
    setLoading(true);
    refreshUser();
    userApi.get("/users/me/transactions")
      .then((r) => {
        if (!cancelled) setTxs(r.data || []);
      })
      .catch(() => {
        if (!cancelled) setTxs([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [userId, refreshUser]);

  useEffect(() => {
    if (!userId) return undefined;
    let cancelled = false;
    setReadingPassEnabled(false);
    setDevices([]);
    setDevicesLoading(false);
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
  }, [userId]);

  if (visualFixture) {
    return <AccountVisualFixture />;
  }

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
    const deviceLabel = formatSessionDeviceLabel(device.device_label);
    if (!target || !window.confirm(`Revoke ${deviceLabel}? Any active Reading Pass lease there will stop.`)) return;
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
      <div className="account-content-container max-w-7xl mx-auto">
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10 sm:mb-12">
          <div className="account-panel account-balance-panel p-7 sm:p-8" data-testid="account-balance-card" role="region" aria-labelledby="account-balance-heading">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80">
              <Clock size={13} strokeWidth={1.5} /> Reading Pass
            </div>
            <h2 id="account-balance-heading" className={`account-balance-value font-serif-display ${PUBLIC_PAID_COMMERCE_ENABLED ? "text-5xl sm:text-6xl" : "text-3xl sm:text-4xl"} text-burgundy mt-4 leading-tight`} data-testid="account-balance">
              {formatMinutes(balance)}
            </h2>
            <div className="gold-rule-thin mt-4" />
            <p className="text-charcoal-soft text-sm font-light mt-5 leading-relaxed">
              {PUBLIC_PAID_COMMERCE_ENABLED && readingPassEnabled
                ? "Reading Pass uses short server leases and a 10-second heartbeat. Reading bills only while protected text is active; listening bills only while approved audio is playing."
                : readingPassEnabled
                ? "Reading time is billed only while protected text is active under a short server-authoritative lease. Hidden tabs, sleeping devices, and long idle gaps are not charged."
                : "The first 3 pages are free where a preview is available. Continuing from page 4 requires a valid Reading Pass; pass purchases are not available yet."}
            </p>
            <p className="mt-3 text-xs leading-relaxed text-charcoal-soft/80" data-testid="account-wallet-explainer">
              Pass purchases are not available yet. Audiobooks are unavailable for this launch.
            </p>
            {!PUBLIC_PAID_COMMERCE_ENABLED && (
              <div className="account-reading-pass-status mt-5 border-t border-brand/30 pt-4" data-testid="account-reading-pass-status">
                <span className="block text-xs font-semibold uppercase tracking-[0.14em] text-burgundy">Reading Pass</span>
                <span className="block mt-1 text-sm text-charcoal-soft">Purchases are not available yet. Your balance remains available for eligible reading.</span>
              </div>
            )}
            <Link
              to="/pricing"
              className="inline-flex items-center gap-2 text-[0.72rem] tracking-[0.22em] uppercase text-burgundy mt-6 hover:opacity-70"
              data-testid="account-buy-time"
              onClick={() => trackFunnelEvent("pricing_page_view", {
                source: "account_wallet",
                book_slug: "dracula",
              })}
            >
              {PUBLIC_PAID_COMMERCE_ENABLED ? "Add reading time" : "Get a Reading Pass"} <ArrowUpRight size={13} strokeWidth={1.5} />
            </Link>
          </div>

          <div className="account-panel account-continue-panel p-7 sm:p-8 flex flex-col">
            <div className="flex items-center gap-2 italic-eyebrow opacity-80">
              <BookOpen size={13} strokeWidth={1.5} /> Continue reading
            </div>
            <p className="font-serif-display text-xl text-charcoal mt-4 leading-snug">
              Continue with any released India title. The first 3 pages are free; page 4 onward requires a valid Reading Pass.
            </p>
            <div className="mt-auto pt-6">
              <Link
                to="/library"
                className="btn-primary w-full sm:w-auto"
                data-testid="account-go-library"
                onClick={() => trackFunnelEvent("return_resume_reading_click", {
                  source: "account_library_destination",
                })}
              >
                Browse the Library
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
              <SessionGroups devices={devices} onRevoke={revokeDevice} />
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
      <div className="account-mobile-navigation">
        <ExperienceBottomNavigation active="profile" onNavigate={onProfileNavigate} />
      </div>
    </div>
  );
}

function SessionRow({ device, onRevoke }) {
  const revoked = device.status !== "active";
  const label = formatSessionDeviceLabel(device.device_label);
  const lastActive = formatSessionLastActive(device.last_seen_at);
  const previousStatus = device.status === "revoked" ? "Revoked" : device.status === "expired" ? "Expired" : device.status === "ended" ? "Signed out" : "Previous session";
  return (
    <li key={device.session_id || device.device_id} className={`account-device-row${device.current ? " is-current" : ""}`}>
      <div className="account-device-row__icon" aria-hidden="true"><MonitorSmartphone size={18} strokeWidth={1.6} /></div>
      <div className="account-device-row__details">
        <div className="account-device-row__title">
          <strong>{label}</strong>
          {device.current && <span className="account-device-row__current">This device</span>}
        </div>
        <span className="account-device-row__activity">
          {device.current ? "Active now" : `${revoked ? previousStatus : "Active session"}${lastActive ? ` · Last active ${lastActive}` : ""}`}
        </span>
      </div>
      {!revoked && (
        <button type="button" onClick={() => onRevoke(device)} className="account-device-row__revoke" aria-label={`Revoke ${label} session`} title={`Revoke ${label} session`}>
          <Trash2 size={16} aria-hidden="true" />
          <span>Revoke</span>
        </button>
      )}
    </li>
  );
}

function SessionGroups({ devices, onRevoke }) {
  const ordered = sortSessionDevices(devices);
  const active = ordered.filter((device) => device.status === "active");
  const previous = ordered.filter((device) => device.status !== "active");
  return (
    <div className="account-session-groups">
      <section aria-labelledby="account-active-sessions-heading" data-testid="account-active-sessions">
        <h3 id="account-active-sessions-heading" className="account-session-group-heading">Active sessions <span>{active.length}</span></h3>
        {active.length ? (
          <ul className="grid gap-3" aria-label="Active sessions">
            {active.map((device) => <SessionRow key={device.session_id || device.device_id} device={device} onRevoke={onRevoke} />)}
          </ul>
        ) : <p className="text-sm text-charcoal-soft">No active sessions.</p>}
      </section>
      {previous.length > 0 && (
        <details className="account-previous-sessions" data-testid="account-previous-sessions">
          <summary>Show previous sessions ({previous.length})</summary>
          <ul className="grid gap-3" aria-label="Previous sessions">
            {previous.map((device) => <SessionRow key={device.session_id || device.device_id} device={device} onRevoke={onRevoke} />)}
          </ul>
        </details>
      )}
    </div>
  );
}
