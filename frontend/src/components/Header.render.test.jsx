import React, { act } from "react";
import { createRoot } from "react-dom/client";

jest.mock("react-router-dom", () => {
  const React = require("react");
  const link = ({ to, children, end, className, ...props }) => React.createElement("a", {
    href: to,
    className: typeof className === "function" ? className({ isActive: false }) : className,
    ...props,
  }, children);
  return {
    Link: link,
    NavLink: ({ className, ...props }) => link({ ...props, className: typeof className === "function" ? className({ isActive: false }) : className }),
    useLocation: () => ({ pathname: "/", search: "", hash: "" }),
    useNavigate: () => jest.fn(),
  };
}, { virtual: true });

jest.mock("../context/SettingsContext", () => ({
  useSettings: () => ({ social: {} }),
}));
jest.mock("../context/AuthContext", () => ({
  useAuth: () => ({ user: false }),
}));

import Header from "./Header";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function renderHeader() {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<Header />));
  return { container, cleanup: () => act(() => { root.unmount(); container.remove(); }) };
}

describe("owner-approved Header composition", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  test("renders the official logo, canonical navigation, search, and a single Sign In action", () => {
    const { container, cleanup } = renderHeader();
    expect(container.querySelector('[data-testid="brand-logo"] img')).not.toBeNull();
    expect(container.querySelector('.premium-header-search input[aria-label="Search books, authors, topics"]')).not.toBeNull();
    expect([...container.querySelectorAll('.premium-header-nav--desktop > a[data-testid^="nav-"]')].map((item) => item.textContent.trim())).toEqual([
      "Home", "Library", "Bengali Classics", "English Classics", "Audiobooks", "Reading Pass", "About", "Sign In",
    ]);
    expect(container.querySelector('[data-testid="nav-sign-in"]')?.getAttribute("href")).toBe("/login");
    expect(container.querySelector('[data-testid="nav-join"]')).toBeNull();
    expect(container.querySelector('[data-testid="nav-sign-in"]')?.textContent).toContain("Sign In");
    expect(container.querySelector(".premium-header-nav")).not.toBeNull();
    expect(container.querySelector('[data-testid="header-cta-library"]')).toBeNull();
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(document.documentElement.clientWidth);
    cleanup();
  });

  test("reveals the canonical mobile navigation and Sign In route from the menu", () => {
    const { container, cleanup } = renderHeader();
    expect(container.querySelector('[data-testid="mobile-header-search"]')).not.toBeNull();
    const toggle = container.querySelector('[data-testid="mobile-menu-toggle"]');
    expect(toggle).not.toBeNull();
    act(() => toggle.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    expect(container.querySelector('[data-testid="mobile-nav-sign-in"]')?.getAttribute("href")).toBe("/login");
    expect([...container.querySelectorAll('[data-testid^="mobile-nav-"]')].slice(0, 8).map((item) => item.textContent)).toEqual([
      "Home", "Library", "Bengali Classics", "English Classics", "Audiobooks", "Reading Pass", "About", "Sign In",
    ]);
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(document.documentElement.clientWidth);
    cleanup();
  });

  test("renders the mobile menu as a modal surface and makes the routed page inert", () => {
    const main = document.createElement("main");
    main.id = "main-content";
    const footer = document.createElement("footer");
    document.body.append(main, footer);
    const { container, cleanup } = renderHeader();
    const toggle = container.querySelector('[data-testid="mobile-menu-toggle"]');
    act(() => toggle.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    const menu = container.querySelector('[data-testid="mobile-menu"]');
    expect(menu?.getAttribute("role")).toBe("dialog");
    expect(menu?.getAttribute("aria-modal")).toBe("true");
    expect(main.hasAttribute("inert")).toBe(true);
    expect(footer.hasAttribute("inert")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
    act(() => menu.querySelector('[aria-label="Close menu"]').dispatchEvent(new MouseEvent("click", { bubbles: true })));
    expect(main.hasAttribute("inert")).toBe(false);
    expect(footer.hasAttribute("inert")).toBe(false);
    cleanup();
  });
});
