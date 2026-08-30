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
    useLocation: () => ({ pathname: "/", search: "" }),
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

  test("renders the desktop logo, navigation, Search, and Sign In without a desktop Library CTA", () => {
    const { container, cleanup } = renderHeader();
    expect(container.querySelector('[data-testid="brand-logo"] img')).not.toBeNull();
    expect(container.querySelector('[data-testid="nav-search"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="nav-sign-in"]')).not.toBeNull();
    expect(container.querySelector(".premium-header-nav")).not.toBeNull();
    expect(container.querySelector('[data-testid="header-cta-library"]')).toBeNull();
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(document.documentElement.clientWidth);
    cleanup();
  });

  test("reveals the approved mobile Library CTA and Sign In route from the menu", () => {
    const { container, cleanup } = renderHeader();
    expect(container.querySelector('[data-testid="mobile-header-search"]')).not.toBeNull();
    const toggle = container.querySelector('[data-testid="mobile-menu-toggle"]');
    expect(toggle).not.toBeNull();
    act(() => toggle.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    const library = container.querySelector('[data-testid="mobile-cta-library"]');
    expect(library?.getAttribute("href")).toBe("/library");
    expect(container.querySelector('[data-testid="mobile-nav-sign-in"]')?.getAttribute("href")).toBe("/login");
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
