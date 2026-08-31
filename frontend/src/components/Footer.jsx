import { Link } from "react-router-dom";
import { ArrowUpRight, Mail } from "lucide-react";
import EarnalismBrandLockup from "./EarnalismBrandLockup";
import { useAuth } from "../context/AuthContext";

const CONTACT_EMAIL = "sales@reoenterprise.org";

export default function Footer() {
  const year = new Date().getFullYear();
  const { user } = useAuth();
  const accountHref = user && typeof user === "object" ? "/account" : "/login";
  const accountLabel = user && typeof user === "object" ? "Account" : "Sign In";

  return (
    <footer className="border-t border-[#d6ad55]/25 bg-[#0d1f19] text-[#fff8e9]" data-testid="site-footer">
      <div className="h-px bg-gradient-to-r from-transparent via-gold-500/70 to-transparent" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-4 sm:py-8">
        <div className="grid gap-4 md:grid-cols-2 md:gap-7 lg:grid-cols-[minmax(0,1.35fr)_minmax(18rem,0.9fr)_minmax(17rem,0.8fr)] lg:items-start lg:gap-10">
          <div data-testid="footer-brand">
            <EarnalismBrandLockup variant="footer" />
            <p id="footer-brand-statement" className="mt-2 max-w-xl font-serif-display text-lg leading-snug text-[#fff8e9] sm:mt-3">
              Timeless Bengali and English literature, made beautiful for every way you read and listen.
            </p>
            <p className="mt-2 max-w-lg text-sm font-light leading-6 text-[#c8c0b1]">
              Return to beloved classics, discover a voice you have never forgotten, and carry your library wherever the day takes you.
            </p>
          </div>

          <nav aria-labelledby="footer-explore-heading">
            <div id="footer-explore-heading" className="overline mb-2.5">Explore</div>
            <ul className="flex flex-wrap gap-x-5 text-sm text-[#c8c0b1]">
              <li><Link to="/library" className="inline-flex min-h-11 min-w-11 items-center justify-center hover:text-[#f2d188] focus-visible:text-[#f2d188] transition-colors">Library</Link></li>
              <li><Link to="/journal" className="inline-flex min-h-11 min-w-11 items-center justify-center hover:text-[#f2d188] focus-visible:text-[#f2d188] transition-colors">Journal</Link></li>
              <li><Link to="/about" className="inline-flex min-h-11 min-w-11 items-center justify-center hover:text-[#f2d188] focus-visible:text-[#f2d188] transition-colors">About</Link></li>
              <li><Link to="/contact" className="inline-flex min-h-11 min-w-11 items-center justify-center hover:text-[#f2d188] focus-visible:text-[#f2d188] transition-colors">Contact</Link></li>
              <li><Link to={accountHref} className="inline-flex min-h-11 min-w-11 items-center justify-center hover:text-[#f2d188] focus-visible:text-[#f2d188] transition-colors">{accountLabel}</Link></li>
            </ul>
          </nav>

          <div className="md:col-span-2 lg:col-span-1 rounded-2xl border border-[#d6ad55]/25 bg-[#172e25] px-4 py-2.5 sm:px-5 sm:py-4" data-testid="footer-contact">
            <div className="overline mb-2">Library desk</div>
            <p className="text-sm leading-5 text-[#c8c0b1]">Rights, partnerships, or a title suggestion?</p>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="mt-2 inline-flex min-h-11 items-center gap-2 text-sm font-medium text-[#f2d188] transition-colors hover:text-[#fff8e9] focus-visible:text-[#fff8e9]"
            >
              <Mail size={16} aria-hidden="true" />
              <span>Write to us</span>
              <ArrowUpRight size={15} aria-hidden="true" />
              <span className="sr-only"> at {CONTACT_EMAIL}</span>
            </a>
          </div>
        </div>
      </div>

      <div className="border-t border-[#d6ad55]/20 bg-[#07110f]">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-3 grid gap-2 lg:grid-cols-[auto_minmax(0,1fr)] lg:items-center lg:gap-8" data-testid="footer-copyright">
          <p className="text-[0.7rem] tracking-wide text-[#c8c0b1]">
            © {year} The Earnalism Digital Library · A Reo Enterprise venture · All rights reserved.
          </p>
          <p className="text-[0.68rem] font-light leading-relaxed text-[#c8c0b1]/75 lg:text-right" data-testid="footer-content-protection">
            Copyright protected. No unauthorized copying, redistribution, scraping, reproduction, or commercial reuse.
          </p>
        </div>
      </div>
    </footer>
  );
}
