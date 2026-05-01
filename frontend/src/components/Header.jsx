import { useState, useEffect } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/shop", label: "Shop" },
  { to: "/journal", label: "Journal" },
  { to: "/about", label: "About" },
  { to: "/publishing", label: "Publishing" },
  { to: "/contact", label: "Contact" },
];

export default function Header() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => { setOpen(false); }, [loc.pathname]);

  return (
    <header className="sticky top-0 z-50 glass-header" data-testid="site-header">
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 h-16 sm:h-20 flex items-center justify-between">
        <Link to="/" className="flex items-baseline gap-2" data-testid="brand-logo">
          <span className="font-serif-display text-2xl sm:text-[28px] font-medium tracking-tight text-burgundy">The Earnalism</span>
          <span className="hidden sm:inline overline">est. boutique</span>
        </Link>

        <nav className="hidden lg:flex items-center gap-9">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              data-testid={`nav-${n.label.toLowerCase()}`}
              className={({ isActive }) =>
                `text-[13px] tracking-[0.18em] uppercase transition-colors ${isActive ? "text-burgundy" : "text-charcoal-soft hover:text-burgundy"}`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden lg:block">
          <Link to="/shop" className="btn-primary" data-testid="header-cta-shop">Explore</Link>
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
          <div className="px-5 py-6 flex flex-col gap-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-testid={`mobile-nav-${n.label.toLowerCase()}`}
                className={({ isActive }) =>
                  `py-3 px-2 text-base tracking-wide border-b border-brand ${isActive ? "text-burgundy" : "text-charcoal"}`
                }
              >
                {n.label}
              </NavLink>
            ))}
            <Link to="/shop" className="btn-primary mt-5 self-start" data-testid="mobile-cta-shop">Explore the Collection</Link>
          </div>
        </div>
      )}
    </header>
  );
}
