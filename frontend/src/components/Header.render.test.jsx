import React, { act } from "react";
import { createRoot } from "react-dom/client";

let mockLocation = { pathname: "/", search: "", hash: "" };

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
    useLocation: () => mockLocation,
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
import ExperienceHeader from "../experiences-v2/shared/ExperienceHeader";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function renderHeader(Component = Header, props = {}) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<Component {...props} />));
  return { container, cleanup: () => act(() => { root.unmount(); container.remove(); }) };
}

describe("owner-approved Header composition", () => {
  afterEach(() => { document.body.innerHTML = ""; mockLocation = { pathname: "/", search: "", hash: "" }; });

  test.each(["/", "/library", "/book/a-ghost-story", "/reader/a-ghost-story", "/pricing", "/account", "/login", "/privacy"])("uses the identical primary header shell on %s", (pathname) => {
    mockLocation = { pathname, search: "", hash: "" };
    const { container, cleanup } = renderHeader();
    expect(container.querySelector("header").className).toBe("sticky top-0 z-50 glass-header premium-site-header");
    expect(container.querySelector('[data-brand-asset="earnalism-brand-lockup.png"]')).not.toBeNull();
    const desktopBlog = container.querySelectorAll('.premium-header-nav--desktop [data-nav-key="journal"]');
    expect(desktopBlog).toHaveLength(1);
    expect(desktopBlog[0].textContent).toBe("Blog");
    expect(desktopBlog[0].getAttribute("href")).toBe("/journal");
    act(() => container.querySelector('[data-testid="mobile-menu-toggle"]').dispatchEvent(new MouseEvent("click", { bubbles: true })));
    const mobileBlog = container.querySelectorAll('[data-testid="mobile-nav-blog"]');
    expect(mobileBlog).toHaveLength(1);
    expect(mobileBlog[0].textContent).toBe("Blog");
    expect(mobileBlog[0].getAttribute("href")).toBe("/journal");
    cleanup();
  });

  test("renders the official logo, canonical navigation, search, and a single Sign In action", () => {
    const { container, cleanup } = renderHeader();
    expect(container.querySelector('[data-testid="brand-logo"] img')).not.toBeNull();
    expect(container.querySelector('.premium-header-search input[aria-label="Search books, authors, topics"]')).not.toBeNull();
    expect([...container.querySelectorAll('.premium-header-nav--desktop > a[data-testid^="nav-"]')].map((item) => item.textContent.trim())).toEqual([
      "Home", "Library", "Bengali Classics", "English Classics", "Audiobooks", "Reading Pass", "Blog", "About", "Sign In",
    ]);
    expect(container.querySelector('[data-testid="nav-sign-in"]')?.getAttribute("href")).toBe("/login");
    expect(container.querySelector('[data-testid="nav-join"]')).toBeNull();
    expect(container.querySelector('[data-testid="nav-sign-in"]')?.textContent).toContain("Sign In");
    expect(container.querySelector(".premium-header-nav")).not.toBeNull();
    expect(container.querySelector('[data-testid="header-cta-library"]')).toBeNull();
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(document.documentElement.clientWidth);
    cleanup();
  });

  test("immersive pages render the same menu, search and account with their safe exit callback", () => {
    const onNavigatePath = jest.fn();
    const { container, cleanup } = renderHeader(ExperienceHeader, { onNavigatePath });
    expect([...container.querySelectorAll('[data-nav-key]')].map((link) => link.textContent)).toEqual([
      "Home", "Library", "Bengali Classics", "English Classics", "Audiobooks", "Reading Pass", "Blog", "About",
    ]);
    expect(container.querySelector('[data-testid="nav-sign-in"]')).not.toBeNull();
    expect(container.querySelector('[role="search"]')).not.toBeNull();
    act(() => container.querySelector('[data-nav-key="journal"]').dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })));
    expect(onNavigatePath).toHaveBeenCalledWith({ key: "journal", to: "/journal", label: "Blog" });
    cleanup();
  });

  test("reveals the canonical mobile navigation and Sign In route from the menu", () => {
    const { container, cleanup } = renderHeader();
    expect(container.querySelector('[data-testid="mobile-header-search"]')).not.toBeNull();
    const toggle = container.querySelector('[data-testid="mobile-menu-toggle"]');
    expect(toggle).not.toBeNull();
    act(() => toggle.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    expect(container.querySelector('[data-testid="mobile-nav-sign-in"]')?.getAttribute("href")).toBe("/login");
    expect([...container.querySelectorAll('[data-testid^="mobile-nav-"]')].slice(0, 9).map((item) => item.textContent)).toEqual([
      "Home", "Library", "Bengali Classics", "English Classics", "Audiobooks", "Reading Pass", "Blog", "About", "Sign In",
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
