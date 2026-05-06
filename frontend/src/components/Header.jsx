import { useState, useEffect } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { Menu, X, Instagram, Facebook, Youtube, Linkedin, Twitter } from "lucide-react";
import { useSettings } from "../context/SettingsContext";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/library", label: "Library" },
  { to: "/journal", label: "Journal" },
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
];

const SOCIALS = [
  { key: "instagram", label: "Instagram", Icon: Instagram },
  { key: "facebook", label: "Facebook", Icon: Facebook },
  { key: "youtube", label: "YouTube", Icon: Youtube },
  { key: "linkedin", label: "LinkedIn", Icon: Linkedin },
  { key: "twitter", label: "X", Icon: Twitter },
];

export default function Header() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  const { social } = useSettings();
  const { user } = useAuth();
  useEffect(() => { setOpen(false); }, [loc.pathname]);
  const activeSocials = SOCIALS.filter((s) => social?.[s.key]);
  const isAuthed = !!user && typeof user === "object";
  const accountHref = isAuthed ? "/account" : "/login";
  const accountLabel = isAuthed ? "Account" : "Sign In";

  return (
    <header className="sticky top-0 z-50 glass-header" data-testid="site-header">
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 h-16 sm:h-20 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-baseline gap-2 sm:gap-3 min-w-0" data-testid="brand-logo">
          <span className="font-serif-light text-[1.35rem] sm:text-[1.65rem] tracking-tight text-burgundy leading-none truncate">The Earnalism</span>
          <span className="hidden md:inline italic-accent text-[0.8rem] text-gold-deep leading-none whitespace-nowrap">Digital Library</span>
        </Link>

        <nav className="hidden lg:flex items-center gap-7 xl:gap-9">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              data-testid={`nav-${n.label.toLowerCase().replace(/\s/g, '-')}`}
              className={({ isActive }) =>
                `text-[0.7rem] tracking-[0.26em] uppercase transition-colors whitespace-nowrap ${isActive ? "text-burgundy" : "text-charcoal-soft hover:text-burgundy"}`
              }
            >
              {n.label}
            </NavLink>
          ))}
          <NavLink
            to={accountHref}
            data-testid={isAuthed ? "nav-account" : "nav-sign-in"}
            className={({ isActive }) =>
              `text-[0.7rem] tracking-[0.26em] uppercase transition-colors whitespace-nowrap ${isActive ? "text-burgundy" : "text-charcoal-soft hover:text-burgundy"}`
            }
          >
            {accountLabel}
          </NavLink>
        </nav>

        <div className="hidden lg:block">
          <Link to="/library" className="btn-secondary" data-testid="header-cta-library">Start Reading</Link>
        </div>

        <button
          aria-label="Open menu"
          onClick={() => setOpen((v) => !v)}
          className="lg:hidden p-2 -mr-2 text-burgundy"
          data-testid="mobile-menu-toggle"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {open && (
        <div className="lg:hidden border-t border-brand bg-ivory/95 backdrop-blur-xl" data-testid="mobile-menu">
          <div className="px-5 py-5 flex flex-col">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-testid={`mobile-nav-${n.label.toLowerCase().replace(/\s/g, '-')}`}
                className={({ isActive }) =>
                  `py-4 text-[0.95rem] tracking-wide border-b border-brand-soft ${isActive ? "text-burgundy" : "text-charcoal"}`
                }
              >
                {n.label}
              </NavLink>
            ))}
            <NavLink
              to={accountHref}
              data-testid={isAuthed ? "mobile-nav-account" : "mobile-nav-sign-in"}
              className={({ isActive }) =>
                `py-4 text-[0.95rem] tracking-wide border-b border-brand-soft ${isActive ? "text-burgundy" : "text-charcoal"}`
              }
            >
              {accountLabel}
            </NavLink>
            <Link to="/library" className="btn-primary mt-7 w-full justify-center" data-testid="mobile-cta-library">Start Reading</Link>

            {activeSocials.length > 0 && (
              <div className="mt-7 pt-5 border-t border-brand-soft flex items-center justify-center gap-5" data-testid="mobile-socials">
                {activeSocials.map(({ key, label, Icon }) => (
                  <a
                    key={key}
                    href={social[key]}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={label}
                    className="text-charcoal-soft hover:text-burgundy transition-colors p-2"
                    data-testid={`mobile-social-${key}`}
                  >
                    <Icon size={18} strokeWidth={1.5} />
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
