import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  Menu,
  X,
  Instagram,
  Facebook,
  Youtube,
  Linkedin,
  Mail,
  Twitter,
  Search,
  UserRound,
} from "lucide-react";
import { useSettings } from "../context/SettingsContext";
import { useAuth } from "../context/AuthContext";
import EarnalismBrandLockup from "./EarnalismBrandLockup";
import { getEnabledSocialLinks } from "../config/socialLinks";
import { PUBLIC_NAV_ITEMS, isPublicNavItemActive } from "../config/publicNavigation";
import "./Header.css";

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
  const [searchQuery, setSearchQuery] = useState("");
  const menuRef = useRef(null);
  const menuToggleRef = useRef(null);
  const returnFocusToMenuToggle = useRef(false);
  const loc = useLocation();
  const navigate = useNavigate();
  const { social } = useSettings();
  const { user } = useAuth();
  useEffect(() => { setOpen(false); }, [loc.pathname, loc.search]);
  const closeMenu = useCallback(({ restoreFocus = true } = {}) => {
    returnFocusToMenuToggle.current = restoreFocus;
    setOpen(false);
  }, []);
  const activeSocials = useMemo(() => (
    getEnabledSocialLinks(social)
      .map((item) => ({ ...item, Icon: SOCIAL_ICONS[item.icon] || SOCIAL_ICONS[item.id] }))
      .filter((item) => item.Icon)
  ), [social]);
  const isAuthed = !!user && typeof user === "object";
  const accountHref = isAuthed ? "/account" : "/login";
  const accountLabel = isAuthed ? "Account" : "Sign In";
  const usesDarkReferenceShell = loc.pathname === "/" || loc.pathname === "/pricing" || loc.pathname.startsWith("/book/");
  const usesHomeOptionBShell = loc.pathname === "/";
  const usesLibraryReferenceShell = loc.pathname === "/library";
  const usesCommerceReferenceShell = loc.pathname === "/pricing";
  const usesProfileMobileShell = loc.pathname === "/account";

  useEffect(() => {
    if (!open) return undefined;
    const main = document.getElementById("main-content");
    const footer = document.querySelector("footer");
    const menuToggle = menuToggleRef.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    [main, footer].filter(Boolean).forEach((element) => {
      element.setAttribute("inert", "");
      element.setAttribute("aria-hidden", "true");
    });
    const focusable = () => [...(menuRef.current?.querySelectorAll("a[href], button:not([disabled])") || [])]
      .filter((element) => element.offsetParent !== null);
    const first = focusable()[0];
    first?.focus();
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeMenu();
        return;
      }
      if (event.key !== "Tab") return;
      const controls = focusable();
      if (!controls.length) return;
      const firstControl = controls[0];
      const lastControl = controls.at(-1);
      if (event.shiftKey && document.activeElement === firstControl) {
        event.preventDefault();
        lastControl.focus();
      } else if (!event.shiftKey && document.activeElement === lastControl) {
        event.preventDefault();
        firstControl.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      [main, footer].filter(Boolean).forEach((element) => {
        element.removeAttribute("inert");
        element.removeAttribute("aria-hidden");
      });
      document.removeEventListener("keydown", onKeyDown);
      if (returnFocusToMenuToggle.current) {
        returnFocusToMenuToggle.current = false;
        requestAnimationFrame(() => menuToggle?.focus());
      }
    };
  }, [open, closeMenu]);
  return (
    <header
      className={`sticky top-0 z-50 glass-header premium-site-header${usesDarkReferenceShell ? " premium-site-header--reference-public" : ""}${usesHomeOptionBShell ? " premium-site-header--reference-home" : ""}${usesLibraryReferenceShell ? " premium-site-header--reference-library" : ""}${usesCommerceReferenceShell ? " premium-site-header--reference-commerce" : ""}${usesProfileMobileShell ? " premium-site-header--reference-profile" : ""}`}
      data-testid="site-header"
    >
      <div className="premium-header-inner max-w-[1536px] mx-auto px-5 sm:px-8 lg:px-10 h-[var(--site-header-height)] flex items-center justify-between gap-4">
        <div className="header-brand-cluster">
          <Link to="/" className="flex items-center min-w-0" data-testid="brand-logo">
            <EarnalismBrandLockup variant="desktop-header" />
          </Link>
        </div>

        <nav className="premium-header-nav premium-header-nav--desktop items-center" aria-label="Primary navigation">
          {PUBLIC_NAV_ITEMS.map((n) => (
            <Link
              key={n.key}
              to={n.to}
              data-testid={`nav-${n.label.toLowerCase().replace(/\s/g, '-')}`}
              className={`tracking-[0.12em] transition-colors whitespace-nowrap ${isPublicNavItemActive(n, loc) ? "text-burgundy" : "text-charcoal-soft hover:text-burgundy"}`}
              aria-current={isPublicNavItemActive(n, loc) ? "page" : undefined}
            >
              {n.label}
            </Link>
          ))}
          <form className="premium-header-search" role="search" data-testid="nav-search" onSubmit={(event) => {
            event.preventDefault();
            const query = searchQuery.trim();
            navigate(query ? `/library?q=${encodeURIComponent(query)}` : "/library");
          }}>
            <Search size={16} strokeWidth={1.6} aria-hidden="true" />
            <input aria-label="Search books, authors, topics" placeholder="Search books, authors, topics..." value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} />
          </form>
          <NavLink
            to={accountHref}
            data-testid={isAuthed ? "nav-account" : "nav-sign-in"}
            className={({ isActive }) =>
              `premium-header-account transition-colors whitespace-nowrap ${isActive ? "text-burgundy" : "text-charcoal-soft hover:text-burgundy"}`
            }
          >
            <UserRound size={17} strokeWidth={1.55} aria-hidden="true" />
            <span>{accountLabel}</span>
          </NavLink>
        </nav>

        <Link
          to="/library"
          className="premium-mobile-search inline-flex min-h-11 min-w-11 items-center justify-center p-2 text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-burgundy"
          aria-label="Search the library"
          data-testid="mobile-header-search"
        >
          <Search size={20} strokeWidth={1.65} aria-hidden="true" />
        </Link>
        <button
          ref={menuToggleRef}
          type="button"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => (open ? closeMenu() : setOpen(true))}
          className="premium-mobile-menu-toggle inline-flex min-h-11 min-w-11 items-center justify-center p-2 -mr-2 text-burgundy"
          data-testid="mobile-menu-toggle"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {open && (
        <div ref={menuRef} id="mobile-menu" className="mobile-menu-overlay" data-testid="mobile-menu" role="dialog" aria-modal="true" aria-label="Primary navigation">
          <div className="mobile-menu-overlay__content">
            <button type="button" className="mobile-menu-overlay__close" onClick={() => closeMenu()} aria-label="Close menu"><X size={22} aria-hidden="true" /></button>
            {PUBLIC_NAV_ITEMS.map((n) => (
              <Link
                key={n.key}
                to={n.to}
                data-testid={`mobile-nav-${n.label.toLowerCase().replace(/\s/g, '-')}`}
                className={`py-4 text-[0.95rem] tracking-wide border-b border-brand-soft ${isPublicNavItemActive(n, loc) ? "text-burgundy" : "text-charcoal"}`}
                aria-current={isPublicNavItemActive(n, loc) ? "page" : undefined}
              >
                {n.label}
              </Link>
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
            <Link to="/library" className="mobile-menu-overlay__cta" data-testid="mobile-cta-library">Enter the Library</Link>
            {activeSocials.length > 0 && (
              <nav className="mobile-menu-overlay__socials" aria-label="Earnalism social links" data-testid="mobile-socials">
                {activeSocials.map(({ id, ariaLabel, external, Icon, url }) => (
                  <a
                    key={id}
                    href={url}
                    target={external ? "_blank" : undefined}
                    rel={external ? "noopener noreferrer" : undefined}
                    aria-label={ariaLabel}
                    className="mobile-menu-overlay__social-link inline-flex h-10 w-10 items-center justify-center rounded-full border border-brand-soft text-charcoal-soft transition-colors duration-300 hover:border-gold hover:text-burgundy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-gold"
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
