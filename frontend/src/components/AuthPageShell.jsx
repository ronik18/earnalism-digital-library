import { Link } from "react-router-dom";
import EarnalismBrandLockup from "./EarnalismBrandLockup";

export default function AuthPageShell({ eyebrow, title, introduction, children, footer, testId }) {
  return (
    <section className="min-h-[80vh] bg-[radial-gradient(circle_at_top,#fffaf0_0%,#f5ebdc_46%,#efe1cf_100%)] px-5 py-12 sm:py-16" data-testid={testId || "auth-page-shell"}>
      <div className="mx-auto grid w-full max-w-5xl overflow-hidden rounded-[1.75rem] border border-burgundy-600/20 bg-[#fffaf1]/95 shadow-[0_24px_80px_-48px_rgba(61,19,19,0.65)] lg:grid-cols-[0.78fr_1.22fr]">
        <aside className="hidden border-r border-burgundy-600/15 bg-[#241a18] p-10 text-[#fff5e4] lg:flex lg:flex-col lg:justify-between">
          <div>
            <div className="rounded-xl bg-[#fff7e9] p-4"><EarnalismBrandLockup variant="auth" /></div>
            <p className="mt-10 font-serif-display text-3xl leading-tight">A library designed for attention, not interruption.</p>
          </div>
          <p className="text-sm leading-6 text-[#f7e6cf]/75">First 3 pages free preview. Listening requires an active Reading Pass.</p>
        </aside>
        <div className="p-7 sm:p-10 lg:p-12">
          <Link to="/" className="inline-flex rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-burgundy lg:hidden" aria-label="The Earnalism home">
            <EarnalismBrandLockup variant="auth" />
          </Link>
          <div className="mt-7 lg:mt-0">
            <div className="italic-eyebrow mb-3">{eyebrow}</div>
            <h1 className="font-serif-light text-3xl leading-tight text-burgundy sm:text-[2.45rem]">{title}</h1>
            <div className="gold-rule-thin mt-5" />
            <p className="mt-5 text-sm font-light leading-relaxed text-charcoal-soft">{introduction}</p>
          </div>
          {children}
          {footer}
        </div>
      </div>
    </section>
  );
}
