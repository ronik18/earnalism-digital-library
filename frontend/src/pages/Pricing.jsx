import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import useSEO from "../hooks/useSEO";
import { BookOpen, Clock, CreditCard, Lock, ShieldCheck } from "lucide-react";
import { api, userApi, formatError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { trackFunnelEvent } from "../lib/funnelAnalytics";

const RAZORPAY_SCRIPT = "https://checkout.razorpay.com/v1/checkout.js";

const PACK_BADGES = {
  "1h": "Best first choice",
  "10h": "Best value",
};

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
  const [searchParams] = useSearchParams();
  const nav = useNavigate();
  const selectedPackId = searchParams.get("pack");
  const couponCode = searchParams.get("coupon");
  const funnelSource = searchParams.get("source");
  const explainerTrackedRef = useRef(false);

  useEffect(() => {
    trackFunnelEvent("pricing_view", {
      selected_pack_id: selectedPackId || "",
      coupon: couponCode || "",
      source: funnelSource || "pricing",
    });
    Promise.all([api.get("/payments/packs"), api.get("/payments/config")])
      .then(([packsRes, configRes]) => {
        const packRows = packsRes.data || [];
        setPacks(packRows);
        setConfig(configRes.data || {});
        packRows.forEach((pack) => {
          trackFunnelEvent("pricing_pack_rendered", {
            pack_id: pack.id,
            label: pack.label,
            minutes: pack.minutes,
            price_inr: pack.price_inr,
            selected: selectedPackId === pack.id,
            source: funnelSource || "pricing",
          });
        });
      })
      .catch(() => setPacks([]));
  }, [couponCode, funnelSource, selectedPackId]);

  useEffect(() => {
    if (explainerTrackedRef.current) return;
    explainerTrackedRef.current = true;
    trackFunnelEvent("reading_time_explainer_rendered", {
      source: funnelSource || "pricing",
      book_slug: "dracula",
    });
  }, [funnelSource]);

  const isAuthed = !!user && typeof user === "object";

  const handleDraculaContinueClick = () => {
    trackFunnelEvent("dracula_continue_from_pricing_click", {
      book_slug: "dracula",
      selected_pack_id: selectedPackId || "",
      source: funnelSource || "pricing",
    });
  };

  const handleBuy = async (pack) => {
    trackFunnelEvent("pricing_pack_cta_click", {
      pack_id: pack.id,
      price_inr: pack.price_inr,
      coupon: couponCode || "",
      source: funnelSource || "pricing",
    });
    trackFunnelEvent("checkout_start", {
      pack_id: pack.id,
      price_inr: pack.price_inr,
      coupon: couponCode || "",
      source: funnelSource || "pricing",
      payment_mode: config.configured ? "razorpay" : config.mode || "unconfigured",
    });
    if (!isAuthed) {
      const next = `${window.location.pathname}${window.location.search}`;
      nav(`/login?next=${encodeURIComponent(next)}`);
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
              trackFunnelEvent("payment_success", {
                pack_id: pack.id,
                price_inr: pack.price_inr,
                minutes: pack.minutes,
                source: "razorpay_verify",
                credited,
              });
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
              trackFunnelEvent("payment_success", {
                pack_id: pack.id,
                price_inr: pack.price_inr,
                minutes: pack.minutes,
                source: "razorpay_webhook_fallback",
                credited,
              });
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
          trackFunnelEvent("payment_failed", {
            pack_id: pack.id,
            price_inr: pack.price_inr,
            reason: resp?.error?.code || "razorpay_failure",
          });
          toast.error(resp?.error?.description || "Payment failed");
        });
        rzp.open();
      } else if (config.mode === "test") {
        // Test-mode simulator (no Razorpay keys yet).
        const { data } = await userApi.post("/payments/_simulate_topup", { pack_id: pack.id });
        await userApi.post(`/payments/_simulate_webhook?intent_id=${data.intent_id}`);
        await refreshUser();
        toast.success(`Test purchase complete · +${pack.minutes} minutes added.`);
        trackFunnelEvent("pricing_test_purchase_complete", { pack_id: pack.id, price_inr: pack.price_inr });
        trackFunnelEvent("payment_success", {
          pack_id: pack.id,
          price_inr: pack.price_inr,
          minutes: pack.minutes,
          source: "test_mode_simulator",
          credited: true,
        });
        nav("/account");
      } else {
        trackFunnelEvent("payment_failed", {
          pack_id: pack.id,
          price_inr: pack.price_inr,
          reason: "payments_unconfigured",
        });
        toast.error("Payments are not configured yet.");
      }
    } catch (err) {
      trackFunnelEvent("payment_failed", {
        pack_id: pack.id,
        price_inr: pack.price_inr,
        reason: err?.response?.status || "checkout_start_failed",
      });
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
            Choose your reading time. <span className="italic-accent">Return whenever</span> the book calls.
          </h1>
          <div className="gold-rule-thin mx-auto mt-7" />
          <p className="text-charcoal-soft text-base sm:text-lg font-light leading-[1.9] mt-7 max-w-2xl mx-auto">
            Start with Chapter 1 free. When you are ready to continue Dracula, add reading time to your wallet. Your time is used only while you read.
          </p>
          <div className="mt-7 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/book/dracula"
              onClick={handleDraculaContinueClick}
              className="btn-secondary"
              data-testid="dracula-continue-from-pricing"
            >
              Continue Dracula
            </Link>
            <span className="text-xs tracking-[0.18em] uppercase text-charcoal-soft">Chapter 1 remains free to preview</span>
          </div>
          {showSimulator && (
            <div className="mt-7 inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--brand-gold)]/40 text-[0.7rem] tracking-[0.22em] uppercase text-gold-deep" data-testid="pricing-test-mode-banner">
              <Lock size={11} strokeWidth={1.5} /> Test mode — Razorpay keys not configured. Purchases use a local simulator.
            </div>
          )}
          {couponCode && (
            <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--brand-gold)]/45 bg-white/50 text-xs tracking-[0.16em] uppercase text-gold-deep">
              Coupon {couponCode} applied at checkout
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 sm:gap-6">
          {packs.map((p) => {
            const selected = selectedPackId === p.id;
            const badge = PACK_BADGES[p.id];
            return (
            <div key={p.id} className={`card-elegant p-7 flex flex-col ${selected ? "pricing-card--selected" : ""}`} data-testid={`pack-${p.id}`} aria-label={selected ? `${p.label}, selected offer` : p.label}>
              <div className="italic-eyebrow opacity-80 flex items-center gap-2"><Clock size={13} strokeWidth={1.5} /> {p.minutes >= 60 ? `${p.minutes / 60} ${p.minutes === 60 ? "hour" : "hours"}` : `${p.minutes} minutes`}</div>
              <div className="flex flex-wrap gap-2 mt-4 min-h-[2rem]">
                {badge && <span className="pricing-card__badge">{badge}</span>}
                {selected && <span className="pricing-card__badge pricing-card__badge--muted">Selected</span>}
              </div>
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
            );
          })}
        </div>

        <section className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-3" aria-label="Reading time wallet explanation" data-testid="pricing-wallet-explainer">
          <div className="rounded-lg border border-brand-soft bg-white/55 p-5">
            <BookOpen size={18} strokeWidth={1.55} className="text-gold" />
            <h2 className="mt-4 font-serif-display text-xl text-burgundy">Chapter 1 stays free</h2>
            <p className="mt-3 text-sm leading-[1.75] text-charcoal-soft">Use the preview to decide whether Dracula has earned your next hour.</p>
          </div>
          <div className="rounded-lg border border-brand-soft bg-white/55 p-5">
            <CreditCard size={18} strokeWidth={1.55} className="text-gold" />
            <h2 className="mt-4 font-serif-display text-xl text-burgundy">Time goes to your wallet</h2>
            <p className="mt-3 text-sm leading-[1.75] text-charcoal-soft">After payment confirmation, reading time is credited to your wallet and can be used when you return.</p>
          </div>
          <div className="rounded-lg border border-brand-soft bg-white/55 p-5">
            <ShieldCheck size={18} strokeWidth={1.55} className="text-gold" />
            <h2 className="mt-4 font-serif-display text-xl text-burgundy">No subscription</h2>
            <p className="mt-3 text-sm leading-[1.75] text-charcoal-soft">This is not a recurring plan, book ownership claim, or autorenewal product.</p>
          </div>
        </section>

        <section className="mt-16 pt-12 border-t border-[var(--border-soft)]/80" aria-labelledby="why-reading-time" data-testid="reading-time-explainer">
          <div className="grid lg:grid-cols-[0.85fr_1.15fr] gap-8 lg:gap-12 items-start">
            <div>
              <div className="italic-eyebrow mb-4">Why reading time?</div>
              <h2 id="why-reading-time" className="font-serif-light text-3xl sm:text-4xl text-burgundy leading-tight">
                A quieter way to pay for reading.
              </h2>
            </div>
            <p className="text-charcoal-soft text-base sm:text-lg font-light leading-[1.9] max-w-3xl">
              Earnalism is a digital reading room. You buy quiet reading time, not a noisy subscription. There is no autorenewal and no pressure to finish before a billing cycle.
            </p>
          </div>
        </section>

        <div className="text-center mt-14">
          <div className="mx-auto grid max-w-3xl grid-cols-1 gap-3 rounded-lg border border-brand-soft bg-white/50 p-5 text-sm text-charcoal-soft sm:grid-cols-2" data-testid="pricing-trust-copy">
            <span>Secure payment by Razorpay.</span>
            <span>No subscription or autorenewal.</span>
            <span>Reading time is credited to your wallet after confirmation.</span>
            <span>For support or refund questions, contact sales@reoenterprise.org.</span>
          </div>
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/contact" className="btn-secondary">Need help?</Link>
            <Link to="/library" className="btn-link" data-testid="pricing-to-library">Browse the library →</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
