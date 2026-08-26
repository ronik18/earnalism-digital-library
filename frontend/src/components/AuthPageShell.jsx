import { Link } from "react-router-dom";
import EarnalismBrandLockup from "./EarnalismBrandLockup";
import "../styles/auth-account.css";

export default function AuthPageShell({ eyebrow, title, introduction, children, footer, testId }) {
  return (
    <section className="auth-account-shell min-h-[80vh] px-5 py-10 sm:py-16" data-testid={testId || "auth-page-shell"}>
      <div className="auth-account-auth-card mx-auto grid w-full max-w-5xl overflow-hidden lg:grid-cols-[0.88fr_1.12fr]">
        <aside className="auth-account-auth-aside hidden p-10 text-[#fff5e4] lg:flex lg:flex-col lg:justify-between">
          <div>
            <div className="auth-account-brand-panel"><EarnalismBrandLockup variant="auth" /></div>
            <p className="auth-account-aside-title mt-10">A library designed for attention, not interruption.</p>
            <div className="auth-account-aside-points" aria-label="Account benefits">
              <span>Keep your place across devices</span>
              <span>See your Reading Pass balance clearly</span>
              <span>Manage access whenever you need to</span>
            </div>
          </div>
          <p className="auth-account-aside-note">Read the first 3 pages free. Listening requires an active Reading Pass.</p>
        </aside>
        <div className="auth-account-auth-content p-7 sm:p-10 lg:p-12">
          <Link to="/" className="auth-account-mobile-brand inline-flex rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-burgundy lg:hidden" aria-label="The Earnalism home">
            <EarnalismBrandLockup variant="auth" />
          </Link>
          <div className="mt-7 lg:mt-0">
            <div className="auth-account-kicker italic-eyebrow mb-3">{eyebrow}</div>
            <h1 className="auth-account-title font-serif-light text-3xl leading-tight text-burgundy sm:text-[2.45rem]">{title}</h1>
            <div className="gold-rule-thin mt-5" />
            <p className="auth-account-introduction mt-5 text-sm font-light leading-relaxed text-charcoal-soft">{introduction}</p>
          </div>
          {children}
          {footer}
        </div>
      </div>
    </section>
  );
}
