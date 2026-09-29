import { Bell, Menu, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import EarnalismBrandLockup from "../../components/EarnalismBrandLockup";
import { PUBLIC_NAV_ITEMS } from "../../config/publicNavigation";
import { useAuth } from "../../context/AuthContext";
import ExperienceIconButton from "./ExperienceIconButton";

export default function ExperienceHeader({ compact = false, onSearch, onNotifications, onNavigate, trailingLabel = "Library", activeNavKey = null }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuToggleRef = useRef(null);
  const auth = useAuth();
  const user = auth?.user;
  const isAuthed = !!user && typeof user === "object";
  const accountHref = isAuthed ? "/account" : "/login";
  const accountLabel = isAuthed ? "Account" : "Sign In";

  useEffect(() => {
    if (!menuOpen) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        requestAnimationFrame(() => menuToggleRef.current?.focus());
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [menuOpen]);

  return (
    <header className={`experience-header ${compact ? "experience-header--compact" : ""}`.trim()} data-testid="experience-header">
      <Link to="/" className="experience-header__brand" aria-label="Earnalism home">
        <EarnalismBrandLockup variant="desktop-header" />
      </Link>
      <div className="experience-header__actions">
        {!compact && (onNavigate
          ? <button type="button" className="experience-header__label experience-header__link" onClick={() => onNavigate("library")}>{trailingLabel}</button>
          : <span className="experience-header__label">{trailingLabel}</span>)}
        {onSearch && <ExperienceIconButton label="Search library" onClick={onSearch}><Search size={17} /></ExperienceIconButton>}
        {onNotifications && <ExperienceIconButton label="Notifications" onClick={onNotifications}><Bell size={17} /></ExperienceIconButton>}
        <button ref={menuToggleRef} type="button" className="experience-icon-button experience-header__menu-toggle" aria-label={menuOpen ? "Close menu" : "Open menu"} aria-expanded={menuOpen} aria-controls="experience-header-menu" onClick={() => setMenuOpen((open) => !open)}>
          {menuOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
        </button>
      </div>
      {menuOpen && <nav id="experience-header-menu" className="experience-header__menu" aria-label="Primary navigation">
        {PUBLIC_NAV_ITEMS.map((item) => <Link key={item.key} data-nav-key={item.key} to={item.to} aria-current={item.key === activeNavKey ? "page" : undefined} onClick={() => setMenuOpen(false)}>{item.label}</Link>)}
        <Link to={accountHref} data-testid={isAuthed ? "experience-menu-account" : "experience-menu-sign-in"} onClick={() => setMenuOpen(false)}>{accountLabel}</Link>
      </nav>}
    </header>
  );
}
