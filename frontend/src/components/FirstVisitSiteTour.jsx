import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowRight, BookOpen, ChevronLeft, ChevronRight, Compass, Sparkles, X } from "lucide-react";
import "./FirstVisitSiteTour.css";

const STORAGE_KEY = "earnalism:first-visit-site-tour:v1";

const TOUR_STEPS = [
  {
    key: "welcome",
    icon: Sparkles,
    targetSelectors: ['[data-testid="brand-logo"]'],
    eyebrow: "A quick orientation",
    title: "Welcome to Earnalism",
    body: "A calm digital reading room beginning with Dracula by Bram Stoker, and the brand promise: Where Learning Becomes Earning.",
  },
  {
    key: "preview",
    icon: BookOpen,
    targetSelectors: ['[data-testid="hero-cta-read"]', '[data-testid="header-cta-library"]'],
    eyebrow: "Start with confidence",
    title: "Read Chapter 1 free",
    body: "Begin Dracula with the free preview. Later chapters use reading time from your wallet only when you choose to continue.",
  },
  {
    key: "covers",
    icon: Compass,
    targetSelectors: ['[data-testid="hero-dracula-card"]', '[data-testid="home-live-dracula"]'],
    eyebrow: "Live controlled release",
    title: "Dracula is the open room",
    body: "The custom Earnalism Dracula cover marks the one approved core reading release. Audiobook experience is in private review.",
  },
  {
    key: "shelves",
    icon: ArrowRight,
    targetSelectors: ['[data-testid="bengali-gothic-pipeline-shelf"]', '[data-testid="pipeline-books"]'],
    eyebrow: "Pipeline stays gated",
    title: "More classics are in review",
    body: "Future titles stay Coming Soon or Notify Me until source, rights, text QA, and publication gates pass.",
  },
];

export default function FirstVisitSiteTour() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState(null);
  const dialogRef = useRef(null);
  const previousFocusRef = useRef(null);
  const openTimerRef = useRef(null);
  const step = TOUR_STEPS[stepIndex];
  const totalSteps = TOUR_STEPS.length;
  const Icon = step.icon;

  const forcedTour = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get("tour") === "1";
  }, [location.search]);

  const completeTour = useCallback(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, "complete");
    } catch (_) {
      // Storage can be unavailable in private modes; closing the tour should still work.
    }
    setOpen(false);
  }, []);

  const updateTargetRect = useCallback(() => {
    if (!open || !step) {
      setTargetRect(null);
      return;
    }

    const target = findVisibleTarget(step.targetSelectors);
    if (!target) {
      setTargetRect(null);
      return;
    }

    const rect = target.getBoundingClientRect();
    setTargetRect({
      top: Math.max(10, rect.top - 8),
      left: Math.max(10, rect.left - 8),
      width: Math.min(window.innerWidth - 20, rect.width + 16),
      height: Math.min(window.innerHeight - 20, rect.height + 16),
    });
  }, [open, step]);

  useEffect(() => {
    if (location.pathname !== "/") {
      setOpen(false);
      return undefined;
    }

    let alreadySeen = false;
    try {
      alreadySeen = window.localStorage.getItem(STORAGE_KEY) === "complete";
    } catch (_) {
      alreadySeen = false;
    }

    if (alreadySeen && !forcedTour) return undefined;

    openTimerRef.current = window.setTimeout(() => {
      previousFocusRef.current = document.activeElement;
      setOpen(true);
    }, forcedTour ? 120 : 850);

    return () => {
      window.clearTimeout(openTimerRef.current);
    };
  }, [forcedTour, location.pathname]);

  useEffect(() => {
    if (!open) {
      setTargetRect(null);
      if (previousFocusRef.current?.focus) {
        previousFocusRef.current.focus({ preventScroll: true });
      }
      return undefined;
    }

    dialogRef.current?.focus({ preventScroll: true });

    const target = findVisibleTarget(step.targetSelectors);
    target?.scrollIntoView?.({ block: "center", inline: "center", behavior: "smooth" });

    const rectTimer = window.setTimeout(updateTargetRect, 260);
    const handleViewportChange = () => window.requestAnimationFrame(updateTargetRect);
    window.addEventListener("resize", handleViewportChange);
    window.addEventListener("scroll", handleViewportChange, true);

    return () => {
      window.clearTimeout(rectTimer);
      window.removeEventListener("resize", handleViewportChange);
      window.removeEventListener("scroll", handleViewportChange, true);
    };
  }, [open, step, updateTargetRect]);

  useEffect(() => {
    if (!open) return undefined;

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        completeTour();
        return;
      }

      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = dialogRef.current.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [completeTour, open]);

  if (!open || location.pathname !== "/") return null;

  const isLastStep = stepIndex === totalSteps - 1;
  const spotlightStyle = targetRect
    ? {
        top: `${targetRect.top}px`,
        left: `${targetRect.left}px`,
        width: `${targetRect.width}px`,
        height: `${targetRect.height}px`,
      }
    : undefined;

  return (
    <div
      className={`site-tour ${targetRect ? "site-tour--has-target" : ""}`}
      data-testid="first-visit-site-tour"
      aria-live="polite"
    >
      <button
        type="button"
        className="site-tour__scrim"
        aria-label="Skip Earnalism site tour"
        onClick={completeTour}
      />

      {targetRect && <div className="site-tour__spotlight" style={spotlightStyle} aria-hidden="true" />}

      <section
        ref={dialogRef}
        className="site-tour__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="site-tour-title"
        aria-describedby="site-tour-body"
        tabIndex={-1}
      >
        <div className="site-tour__topline">
          <span className="site-tour__badge">
            <Icon size={15} strokeWidth={1.7} aria-hidden="true" />
            {step.eyebrow}
          </span>
          <button type="button" className="site-tour__icon-button" onClick={completeTour} aria-label="Skip site tour">
            <X size={17} strokeWidth={1.7} aria-hidden="true" />
          </button>
        </div>

        <div className="site-tour__progress" aria-label={`Step ${stepIndex + 1} of ${totalSteps}`}>
          {TOUR_STEPS.map((item, index) => (
            <span
              key={item.key}
              className={index <= stepIndex ? "site-tour__progress-dot site-tour__progress-dot--active" : "site-tour__progress-dot"}
            />
          ))}
        </div>

        <p className="site-tour__count">Step {stepIndex + 1} of {totalSteps}</p>
        <h2 id="site-tour-title" className="site-tour__title">{step.title}</h2>
        <p id="site-tour-body" className="site-tour__body">{step.body}</p>

        <div className="site-tour__actions">
          <button type="button" className="site-tour__skip" onClick={completeTour}>
            Skip tour
          </button>
          <div className="site-tour__nav">
            <button
              type="button"
              className="site-tour__nav-button"
              onClick={() => setStepIndex((value) => Math.max(0, value - 1))}
              disabled={stepIndex === 0}
              aria-label="Previous tour step"
            >
              <ChevronLeft size={16} strokeWidth={1.7} aria-hidden="true" />
            </button>
            {isLastStep ? (
              <Link to="/library" className="site-tour__primary" onClick={completeTour}>
                Explore Library <ArrowRight size={14} strokeWidth={1.8} aria-hidden="true" />
              </Link>
            ) : (
              <button
                type="button"
                className="site-tour__primary"
                onClick={() => setStepIndex((value) => Math.min(totalSteps - 1, value + 1))}
              >
                Next <ChevronRight size={15} strokeWidth={1.8} aria-hidden="true" />
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function findVisibleTarget(selectors = []) {
  if (typeof document === "undefined") return null;

  for (const selector of selectors) {
    const elements = Array.from(document.querySelectorAll(selector));
    const visible = elements.find((element) => {
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      return rect.width > 12 && rect.height > 12 && style.visibility !== "hidden" && style.display !== "none";
    });
    if (visible) return visible;
  }

  return null;
}
