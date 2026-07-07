import { useState, useEffect, useMemo } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { Menu, X, Instagram, Facebook, Youtube, Linkedin, Mail, Twitter } from "lucide-react";
import { useSettings } from "../context/SettingsContext";
import { useAuth } from "../context/AuthContext";
import BrandMark from "./BrandMark";
import IndiaCraftBadge from "./IndiaCraftBadge";
import { getEnabledSocialLinks } from "../config/socialLinks";

const NAV = [
  { to: "/library", label: "Library" },
  { to: "/library?language=bn&availability=reader-ready", label: "Bengali Classics" },
  { to: "/library?language=en", label: "English Classics" },
  { to: "/library?availability=reader-ready", label: "Reader" },
  { to: "/about", label: "About" },
];

const SOCIAL_ICONS = {
  email: Mail,
  facebook: Facebook,
  instagram: Instagram,
  linkedin: Linkedin,
  x: Twitter,
  youtube: Youtube,
};

export default function Header() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  const { social } = useSettings();
  const { user } = useAuth();
  useEffect(() => { setOpen(false); }, [loc.pathname]);
  const activeSocials = useMemo(() => (
    getEnabledSocialLinks(social)
      .map((item) => ({ ...item, Icon: SOCIAL_ICONS[item.icon] || SOCIAL_ICONS[item.id] }))
      .filter((item) => item.Icon)
  ), [social]);
  const isAuthed = !!user && typeof user === "object";
  const accountHref = isAuthed ? "/account" : "/login";
  const accountLabel = isAuthed ? "Account" : "Sign In";

  return (
    <header className="sticky top-0 z-50 glass-header" data-testid="site-header">
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 h-16 sm:h-20 flex items-center justify-between gap-4">
        <div className="header-brand-cluster">
          <Link to="/" className="flex items-center min-w-0" data-testid="brand-logo" aria-label="Earnalism Where Learning Becomes Earning — Home">
            <BrandMark variant="header" />
          </Link>
          <IndiaCraftBadge />
        </div>

        <nav className="hidden lg:flex items-center gap-7 xl:gap-9">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              data-testid={`nav-${n.label.toLowerCase().replace(/\s/g, '-')}`}
              className={({ isActive }) =>
                `text-[0.88rem] tracking-[0.12em] transition-colors whitespace-nowrap ${isActive ? "text-burgundy" : "text-charcoal-soft hover:text-burgundy"}`
              }
            >
              {n.label}
            </NavLink>
          ))}
          <NavLink
            to={accountHref}
            data-testid={isAuthed ? "nav-account" : "nav-sign-in"}
            className={({ isActive }) =>
              `text-[0.88rem] tracking-[0.12em] transition-colors whitespace-nowrap ${isActive ? "text-burgundy" : "text-charcoal-soft hover:text-burgundy"}`
            }
          >
            {accountLabel}
          </NavLink>
        </nav>

        <div className="hidden lg:block">
          <Link to="/library" className="btn-secondary" data-testid="header-cta-library">Enter Library</Link>
        </div>

        <button
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen((v) => !v)}
          className="lg:hidden p-2 -mr-2 text-burgundy"
          data-testid="mobile-menu-toggle"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {open && (
        <div id="mobile-menu" className="lg:hidden border-t border-brand bg-ivory/95 backdrop-blur-xl" data-testid="mobile-menu">
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
            <Link to="/library" className="btn-primary mt-7 w-full justify-center" data-testid="mobile-cta-library">Enter Library</Link>

            {activeSocials.length > 0 && (
              <nav className="mt-7 pt-5 border-t border-brand-soft flex items-center justify-center gap-4" aria-label="Earnalism social links" data-testid="mobile-socials">
                {activeSocials.map(({ id, ariaLabel, external, Icon, url }) => (
                  <a
                    key={id}
                    href={url}
                    target={external ? "_blank" : undefined}
                    rel={external ? "noopener noreferrer" : undefined}
                    aria-label={ariaLabel}
                    className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-brand-soft text-charcoal-soft transition-colors duration-300 hover:border-gold hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-gold"
                    data-testid={`mobile-social-${id}`}
                  >
                    <Icon size={17} strokeWidth={1.5} aria-hidden="true" />
                  </a>
                ))}
              </nav>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
