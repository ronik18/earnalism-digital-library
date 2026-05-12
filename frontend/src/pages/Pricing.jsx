import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import useSEO from "../hooks/useSEO";
import { Clock, Lock } from "lucide-react";
import { api, userApi, formatError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

const RAZORPAY_SCRIPT = "https://checkout.razorpay.com/v1/checkout.js";

function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (typeof window === "undefined") return resolve(false);
    if (window.Razorpay) return resolve(true);
    const existing = document.querySelector(`script[src="${RAZORPAY_SCRIPT}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve(true));
      existing.addEventListener("error", () => resolve(false));
      return;
    }
    const s = document.createElement("script");
    s.src = RAZORPAY_SCRIPT;
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

export default function Pricing() {
  useSEO({
    title: "Reading Time — The Earnalism Digital Library",
    description: "Reading-time packs at The Earnalism. Buy minutes, read at your own pace, and return whenever you wish.",
  });
  const { user, refreshUser } = useAuth();
  const [packs, setPacks] = useState([]);
  const [config, setConfig] = useState({ configured: false, mode: "test", key_id: "" });
  const [busyId, setBusyId] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    Promise.all([api.get("/payments/packs"), api.get("/payments/config")])
      .then(([packsRes, configRes]) => {
        setPacks(packsRes.data || []);
        setConfig(configRes.data || {});
      })
      .catch(() => setPacks([]));
  }, []);

  const isAuthed = !!user && typeof user === "object";

  const handleBuy = async (pack) => {
    if (!isAuthed) {
      nav(`/login?next=/pricing`);
      return;
    }
    setBusyId(pack.id);
    try {
      if (config.configured) {
        // Real Razorpay Checkout flow.
        const ok = await loadRazorpayScript();
        if (!ok) {
          toast.error("Could not load Razorpay. Please retry.");
          return;
        }
        const { data } = await userApi.post("/payments/topup", { pack_id: pack.id });
        const opts = {
          key: data.key_id,
          amount: data.amount,
          currency: data.currency,
          name: data.name,
          description: data.description,
          order_id: data.razorpay_order_id,
          prefill: data.prefill,
          notes: { intent_id: data.intent_id, pack_id: pack.id },
          theme: { color: "#5C1A1B" },
          handler: async (resp) => {
            // Razorpay's success handler. The modal has already closed and the
            // payment is captured at Razorpay. We try to verify server-side so
            // the wallet credit is immediate; if verify fails for any reason
            // (transient network blip, token expired, etc.) the webhook is the
            // safety net — and we still take the user to /account so they can
            // see their up-to-date balance.
            try {
              await userApi.post("/payments/verify", {
                razorpay_order_id: resp.razorpay_order_id,
                razorpay_payment_id: resp.razorpay_payment_id,
                razorpay_signature: resp.razorpay_signature,
              });
              const fresh = await refreshUser();
              const credited = Number(fresh?.reading_seconds_balance || 0) > 0;
              toast.success(credited ? `+${pack.minutes} minutes added.` : `Payment received. Credit will appear shortly.`);
            } catch (err) {
              // Verify call itself failed. Don't leave the user stuck on
              // /pricing — refresh wallet (webhook may already have credited)
              // and route to /account where they can confirm their balance.
              if (process.env.NODE_ENV === "development") {
                // eslint-disable-next-line no-console
                console.warn("Razorpay verify failed; falling back to /account");
              }
              const fresh = await refreshUser().catch(() => null);
              const credited = Number(fresh?.reading_seconds_balance || 0) > 0;
              if (credited) {
                toast.success(`+${pack.minutes} minutes added.`);
              } else {
                toast.message("Payment received. Your reading time will appear within a minute.");
              }
            } finally {
              nav("/account");
            }
          },
          modal: {
            ondismiss: () => { /* closed without paying */ },
          },
        };
        const rzp = new window.Razorpay(opts);
        rzp.on("payment.failed", (resp) => {
          toast.error(resp?.error?.description || "Payment failed");
        });
        rzp.open();
      } else if (config.mode === "test") {
        // Test-mode simulator (no Razorpay keys yet).
        const { data } = await userApi.post("/payments/_simulate_topup", { pack_id: pack.id });
        await userApi.post(`/payments/_simulate_webhook?intent_id=${data.intent_id}`);
        await refreshUser();
        toast.success(`Test purchase complete · +${pack.minutes} minutes added.`);
        nav("/account");
      } else {
        toast.error("Payments are not configured yet.");
      }
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || "Could not start payment");
    } finally {
      setBusyId(null);
    }
  };

  const showSimulator = !config.configured && config.mode === "test";

  return (
    <div className="min-h-[70vh] px-5 sm:px-8 lg:px-12 py-16 sm:py-24" data-testid="pricing-page">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <div className="italic-eyebrow">Reading time, by the pack</div>
          <h1 className="font-serif-light text-4xl sm:text-5xl lg:text-[3.5rem] text-burgundy leading-[1.05] mt-3 max-w-3xl mx-auto">
            Pay for the minutes you <span className="italic-accent">actually</span> read.
          </h1>
          <div className="gold-rule-thin mx-auto mt-7" />
          <p className="text-charcoal-soft text-base sm:text-lg font-light leading-[1.9] mt-7 max-w-2xl mx-auto">
            No subscriptions. No autorenewals. No pressure to finish before a billing cycle. Choose a pack, open a book, and the clock only runs while the words do.
          </p>
          {showSimulator && (
            <div className="mt-7 inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--brand-gold)]/40 text-[0.7rem] tracking-[0.22em] uppercase text-gold-deep" data-testid="pricing-test-mode-banner">
              <Lock size={11} strokeWidth={1.5} /> Test mode — Razorpay keys not configured. Purchases use a local simulator.
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 sm:gap-6">
          {packs.map((p) => (
            <div key={p.id} className="card-elegant p-7 flex flex-col" data-testid={`pack-${p.id}`}>
              <div className="italic-eyebrow opacity-80 flex items-center gap-2"><Clock size={13} strokeWidth={1.5} /> {p.minutes >= 60 ? `${p.minutes / 60} ${p.minutes === 60 ? "hour" : "hours"}` : `${p.minutes} minutes`}</div>
              <h3 className="font-serif-display text-2xl text-burgundy leading-snug mt-3">{p.label}</h3>
              <div className="font-serif-light text-4xl text-charcoal mt-5">₹{p.price_inr}</div>
              <p className="text-charcoal-soft text-sm font-light leading-relaxed mt-4">{p.note}</p>
              <button
                onClick={() => handleBuy(p)}
                disabled={busyId === p.id}
                className="btn-primary w-full mt-7 disabled:opacity-60"
                data-testid={`pack-${p.id}-buy`}
              >
                {busyId === p.id
                  ? "Working…"
                  : !isAuthed ? "Sign in to buy"
                  : showSimulator ? "Run test purchase"
                  : "Buy reading time"}
              </button>
            </div>
          ))}
        </div>

        <div className="text-center mt-14">
          <p className="text-sm text-charcoal-soft font-light italic max-w-xl mx-auto">
            Payments are processed securely by Razorpay. Your reading time is credited the moment payment is confirmed.
          </p>
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/contact" className="btn-secondary">Need help?</Link>
            <Link to="/library" className="btn-link" data-testid="pricing-to-library">Browse the library →</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
