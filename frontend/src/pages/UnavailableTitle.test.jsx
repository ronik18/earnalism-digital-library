import React, { act } from "react";
import { createRoot } from "react-dom/client";

jest.mock("../hooks/useSEO", () => jest.fn());
jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => require("react").createElement("a", { ...props, href: to }, children),
}), { virtual: true });

import UnavailableTitle from "./UnavailableTitle";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("historical title release hold page", () => {
  test("renders truthful recovery links without loading protected title data", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    const originalFetch = global.fetch;
    global.fetch = jest.fn(() => { throw new Error("unavailable page must not fetch title data"); });

    try {
      act(() => root.render(<UnavailableTitle />));
      expect(container.querySelector("h1").textContent).toBe("Dracula is not currently available.");
      expect(container.textContent).toContain("not part of the current public release");
      expect(container.textContent).toContain("No book text, reader session, or audio is available");
      expect(container.querySelector('[data-testid="unavailable-title-library-link"]').getAttribute("href")).toBe("/library");
      expect(container.querySelector('[data-testid="unavailable-title-contact-link"]').getAttribute("href")).toBe("/contact?interest=dracula");
      expect(global.fetch).not.toHaveBeenCalled();
    } finally {
      global.fetch = originalFetch;
      act(() => root.unmount());
      container.remove();
    }
  });

  test("uses the historical title identity in recovery links without fetching its content", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    const originalFetch = global.fetch;
    global.fetch = jest.fn(() => { throw new Error("unavailable page must not fetch title data"); });

    try {
      act(() => root.render(<UnavailableTitle title="The Selfish Giant" slug="the-selfish-giant" />));
      expect(container.querySelector("h1").textContent).toBe("The Selfish Giant is not currently available.");
      expect(container.querySelector('[data-testid="unavailable-title-contact-link"]').getAttribute("href")).toBe("/contact?interest=the-selfish-giant");
      expect(global.fetch).not.toHaveBeenCalled();
    } finally {
      global.fetch = originalFetch;
      act(() => root.unmount());
      container.remove();
    }
  });
});
