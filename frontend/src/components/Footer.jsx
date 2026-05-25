import { Link } from "react-router-dom";
import { Instagram, Facebook, Youtube, Linkedin, Twitter, Mail } from "lucide-react";
import { useSettings } from "../context/SettingsContext";
import BrandMark from "./BrandMark";

const SOCIALS = [
  { key: "instagram", label: "Instagram", Icon: Instagram },
  { key: "facebook", label: "Facebook", Icon: Facebook },
  { key: "youtube", label: "YouTube", Icon: Youtube },
  { key: "linkedin", label: "LinkedIn", Icon: Linkedin },
  { key: "twitter", label: "X", Icon: Twitter },
];

export default function Footer() {
  const { social } = useSettings();
  const activeSocials = SOCIALS.filter((s) => social?.[s.key]);
  const year = new Date().getFullYear();

  return (
    <footer className="mt-24 sm:mt-32 border-t border-brand bg-ivory" data-testid="site-footer">
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-14 sm:py-20 grid grid-cols-1 md:grid-cols-4 gap-12">
        <div className="md:col-span-2">
          <div className="mb-4 leading-none" data-testid="footer-brand"><BrandMark variant="footer" /></div>
          <p className="font-serif-display italic text-base text-charcoal-soft mb-4">Buy reading time. Read beautifully. Return whenever you wish.</p>
          <p className="text-charcoal-soft max-w-md leading-[1.8] font-light text-[0.95rem]">
            A quiet digital reading room for Bengali classics, literary fiction, young readers, business, technology and AI, history, adventure, science fiction, and gothic fiction.
          </p>
          <div className="gold-rule-thin mt-7" />
        </div>

        <div>
          <div className="overline mb-4">Read</div>
          <ul className="space-y-2 text-charcoal-soft">
            <li><Link to="/library" className="hover:text-burgundy transition-colors">Library</Link></li>
            <li><Link to="/journal" className="hover:text-burgundy transition-colors">Journal</Link></li>
            <li><Link to="/about" className="hover:text-burgundy transition-colors">About</Link></li>
            <li><Link to="/contact" className="hover:text-burgundy transition-colors">Contact</Link></li>
            <li><Link to="/login" className="hover:text-burgundy transition-colors">Sign In</Link></li>
          </ul>
        </div>

        <div>
          <div className="overline mb-4">Reach</div>
          <a href="mailto:hello@theearnalism.com" className="flex items-center gap-2 text-charcoal-soft hover:text-burgundy">
            <Mail size={16} /> hello@theearnalism.com
          </a>
          {activeSocials.length > 0 && (
            <div className="flex gap-3 mt-5 text-charcoal-soft" data-testid="footer-socials">
              {activeSocials.map(({ key, label, Icon }) => (
                <a
                  key={key}
                  href={social[key]}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={label}
                  className="hover:text-burgundy transition-colors"
                  data-testid={`footer-social-${key}`}
                >
                  <Icon size={18} />
                </a>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Copyright + content protection */}
      <div className="border-t border-brand">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-5 flex flex-col md:flex-row items-center justify-between gap-3" data-testid="footer-copyright">
          <p className="text-xs tracking-wider text-charcoal-soft">© {year} The Earnalism Digital Library. All rights reserved.</p>
          <p className="text-xs tracking-wider text-charcoal-soft">Crafted with care · theearnalism.com</p>
        </div>
        <div className="border-t border-brand-soft">
          <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-4">
            <p className="text-[0.7rem] leading-relaxed text-charcoal-soft/80 font-light text-center md:text-left" data-testid="footer-content-protection">
              All books, excerpts, reader pages, journal posts, and digital library materials are protected by copyright. Unauthorized copying, redistribution, screenshot-based reproduction, scraping, or commercial reuse is prohibited.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
