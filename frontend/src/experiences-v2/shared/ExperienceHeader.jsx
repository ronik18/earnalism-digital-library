import { Bell, Menu, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import EarnalismBrandLockup from "../../components/EarnalismBrandLockup";
import { PUBLIC_NAV_ITEMS } from "../../config/publicNavigation";
import { useAuth } from "../../context/AuthContext";
import ExperienceIconButton from "./ExperienceIconButton";

export default function ExperienceHeader({ compact = false, onSearch, onNotifications, onNavigate, onNavigatePath, trailingLabel = "Library", activeNavKey = null, showDesktopNavigation = false }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuToggleRef = useRef(null);
  const auth = useAuth();
  const user = auth?.user;
  const isAuthed = !!user && typeof user === "object";
  const accountHref = isAuthed ? "/account" : "/login";
  const accountLabel = isAuthed ? "Account" : "Sign In";
  const activatePath = (event, item) => {
    if (!onNavigatePath) return;
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onNavigatePath(item);
  };

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
      <Link to="/" className="experience-header__brand" aria-label="Earnalism home" onClick={(event) => { if (onNavigatePath) { event.preventDefault(); onNavigatePath({ key: "home", to: "/", label: "Home" }); } }}>
        <EarnalismBrandLockup variant="desktop-header" />
      </Link>
      {showDesktopNavigation && <nav className="experience-header__desktop-nav" aria-label="Primary navigation">
        {PUBLIC_NAV_ITEMS.map((item) => onNavigatePath
          ? <a key={item.key} href={item.to} data-nav-key={item.key} aria-current={item.key === activeNavKey ? "page" : undefined} onClick={(event) => activatePath(event, item)}>{item.label}</a>
          : <Link key={item.key} data-nav-key={item.key} to={item.to} aria-current={item.key === activeNavKey ? "page" : undefined}>{item.label}</Link>)}
      </nav>}
      <div className="experience-header__actions">
        {!compact && !showDesktopNavigation && (onNavigate
          ? <button type="button" className="experience-header__label experience-header__link" onClick={() => onNavigate("library")}>{trailingLabel}</button>
          : <span className="experience-header__label">{trailingLabel}</span>)}
        {onSearch && <ExperienceIconButton label="Search library" onClick={onSearch}><Search size={17} /></ExperienceIconButton>}
        {onNotifications && <ExperienceIconButton label="Notifications" onClick={onNotifications}><Bell size={17} /></ExperienceIconButton>}
        <button ref={menuToggleRef} type="button" className="experience-icon-button experience-header__menu-toggle" aria-label={menuOpen ? "Close menu" : "Open menu"} aria-expanded={menuOpen} aria-controls="experience-header-menu" onClick={() => setMenuOpen((open) => !open)}>
          {menuOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
        </button>
      </div>
      {menuOpen && <nav id="experience-header-menu" className="experience-header__menu" aria-label="Primary navigation">
        {PUBLIC_NAV_ITEMS.map((item) => onNavigatePath
          ? <a key={item.key} href={item.to} data-nav-key={item.key} aria-current={item.key === activeNavKey ? "page" : undefined} onClick={(event) => { activatePath(event, item); if (event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) setMenuOpen(false); }}>{item.label}</a>
          : <Link key={item.key} data-nav-key={item.key} to={item.to} aria-current={item.key === activeNavKey ? "page" : undefined} onClick={() => setMenuOpen(false)}>{item.label}</Link>)}
        {onNavigatePath
          ? <a href={accountHref} data-testid={isAuthed ? "experience-menu-account" : "experience-menu-sign-in"} onClick={(event) => { activatePath(event, { key: isAuthed ? "profile" : "signin", to: accountHref, label: accountLabel }); if (event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) setMenuOpen(false); }}>{accountLabel}</a>
          : <Link to={accountHref} data-testid={isAuthed ? "experience-menu-account" : "experience-menu-sign-in"} onClick={() => setMenuOpen(false)}>{accountLabel}</Link>}
      </nav>}
    </header>
  );
}
