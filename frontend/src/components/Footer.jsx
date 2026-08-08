import { Link } from "react-router-dom";
import { ArrowUpRight, Mail } from "lucide-react";

const CONTACT_EMAIL = "sales@reoenterprise.org";

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-burgundy-600/20 bg-[#f8f1e5] text-charcoal" data-testid="site-footer">
      <div className="h-px bg-gradient-to-r from-transparent via-gold-500/70 to-transparent" aria-hidden="true" />

      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-4 sm:py-8">
        <div className="grid gap-4 md:grid-cols-2 md:gap-7 lg:grid-cols-[minmax(0,1.35fr)_minmax(18rem,0.9fr)_minmax(17rem,0.8fr)] lg:items-start lg:gap-10">
          <div data-testid="footer-brand">
            <img
              src={`${process.env.PUBLIC_URL || ""}/assets/brand/earnalism-logo-text.png`}
              alt="Earnalism — Where Learning Becomes Earning, a Reo Enterprise venture"
              loading="lazy"
              decoding="async"
              width="1400"
              height="500"
              className="h-auto w-44 max-w-full object-contain object-left sm:w-56"
            />
            <p id="footer-brand-statement" className="mt-2 max-w-xl font-serif-display text-lg leading-snug text-burgundy sm:mt-3">
              Bengali and English classics, presented with quiet release truth.
            </p>
            <p className="mt-2 max-w-lg text-sm font-light leading-6 text-charcoal-soft">
              Reader-ready classics stay visible; audiobooks appear only after evidence proves they are ready.
            </p>
          </div>

          <nav aria-labelledby="footer-explore-heading">
            <div id="footer-explore-heading" className="overline mb-2.5">Explore</div>
            <ul className="flex flex-wrap gap-x-5 text-sm text-charcoal-soft">
              <li><Link to="/library" className="inline-flex min-h-11 items-center hover:text-burgundy focus-visible:text-burgundy transition-colors">Library</Link></li>
              <li><Link to="/journal" className="inline-flex min-h-11 items-center hover:text-burgundy focus-visible:text-burgundy transition-colors">Journal</Link></li>
              <li><Link to="/about" className="inline-flex min-h-11 items-center hover:text-burgundy focus-visible:text-burgundy transition-colors">About</Link></li>
              <li><Link to="/contact" className="inline-flex min-h-11 items-center hover:text-burgundy focus-visible:text-burgundy transition-colors">Contact</Link></li>
              <li><Link to="/login" className="inline-flex min-h-11 items-center hover:text-burgundy focus-visible:text-burgundy transition-colors">Sign In</Link></li>
            </ul>
          </nav>

          <div className="md:col-span-2 lg:col-span-1 rounded-2xl border border-burgundy-600/15 bg-white/45 px-4 py-2.5 sm:px-5 sm:py-4" data-testid="footer-contact">
            <div className="overline mb-2">Library desk</div>
            <p className="text-sm leading-5 text-charcoal-soft">Rights, partnerships, or a title suggestion?</p>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="mt-2 inline-flex min-h-11 items-center gap-2 text-sm font-medium text-burgundy transition-colors hover:text-gold-600 focus-visible:text-gold-600"
            >
              <Mail size={16} aria-hidden="true" />
              <span>Write to us</span>
              <ArrowUpRight size={15} aria-hidden="true" />
              <span className="sr-only"> at {CONTACT_EMAIL}</span>
            </a>
          </div>
        </div>
      </div>

      <div className="border-t border-burgundy-600/15 bg-white/25">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-3 grid gap-2 lg:grid-cols-[auto_minmax(0,1fr)] lg:items-center lg:gap-8" data-testid="footer-copyright">
          <p className="text-[0.7rem] tracking-wide text-charcoal-soft">
            © {year} The Earnalism Digital Library · A Reo Enterprise venture · All rights reserved.
          </p>
          <p className="text-[0.68rem] font-light leading-relaxed text-charcoal-soft/75 lg:text-right" data-testid="footer-content-protection">
            Copyright protected. No unauthorized copying, redistribution, scraping, reproduction, or commercial reuse.
          </p>
        </div>
      </div>
    </footer>
  );
}
