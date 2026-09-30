import React, { act } from "react";
import { createRoot } from "react-dom/client";

const mockPost = jest.fn();
const mockTrackFunnelEvent = jest.fn();
const mockToastSuccess = jest.fn();
const mockToastError = jest.fn();

jest.mock("../lib/api", () => ({
  api: { get: jest.fn(), post: (...args) => mockPost(...args) },
  formatError: (detail) => detail || "Something went wrong. Please try again.",
}));
jest.mock("../lib/funnelAnalytics", () => ({ trackFunnelEvent: (...args) => mockTrackFunnelEvent(...args) }));
jest.mock("sonner", () => ({ toast: { success: (...args) => mockToastSuccess(...args), error: (...args) => mockToastError(...args) } }));
jest.mock("../hooks/useSEO", () => jest.fn());
jest.mock("../lib/controlledLaunch", () => ({
  LIVE_APPROVED_SLUG: "a-ghost-story",
  PUBLIC_AUDIO_EXPOSURE_ENABLED: false,
  PUBLIC_PAID_COMMERCE_ENABLED: false,
}));
jest.mock("../components/EditorialHomeLibrarySurfaces", () => ({
  ReferenceHomeSurface: () => <main>Earnalism Home</main>,
}));

import Home from "./Home";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function mountHome() {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<Home />));
  return { container, cleanup: () => act(() => { root.unmount(); container.remove(); }) };
}

function setInputValue(input, value) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
  act(() => {
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function submitForm(container) {
  await act(async () => {
    container.querySelector('[data-testid="newsletter-card"]').requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("Reading Circle newsletter form", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    mockPost.mockReset();
    mockPost.mockResolvedValue({ data: { message: "Thanks for joining." } });
    mockTrackFunnelEvent.mockReset();
    mockToastSuccess.mockReset();
    mockToastError.mockReset();
  });

  afterEach(() => { document.body.innerHTML = ""; });

  test("renders required name and email fields with browser validation", () => {
    const { container, cleanup } = mountHome();
    expect(container.querySelector('[data-testid="newsletter-card"]')).not.toBeNull();
    expect(container.querySelector('#newsletter-status').textContent).toBe("");
    const name = container.querySelector('[data-testid="newsletter-name"]');
    const email = container.querySelector('[data-testid="newsletter-email"]');
    expect(name.required).toBe(true);
    expect(email.required).toBe(true);
    expect(email.type).toBe("email");
    expect(name.checkValidity()).toBe(false);
    expect(email.checkValidity()).toBe(false);
    expect(mockPost).not.toHaveBeenCalled();
    cleanup();
  });

  test("sends valid input and renders the success state without tracking submitted identity", async () => {
    const { container, cleanup } = mountHome();
    setInputValue(container.querySelector('[data-testid="newsletter-name"]'), "Reader Example");
    setInputValue(container.querySelector('[data-testid="newsletter-email"]'), "reader@example.test");
    await submitForm(container);
    expect(mockPost).toHaveBeenCalledWith("/newsletter", { name: "Reader Example", email: "reader@example.test" });
    expect(container.querySelector('#newsletter-status').textContent).toContain("Welcome to the Reading Circle");
    expect(JSON.stringify(mockTrackFunnelEvent.mock.calls)).not.toContain("reader@example.test");
    expect(JSON.stringify(mockTrackFunnelEvent.mock.calls)).not.toContain("Reader Example");
    cleanup();
  });

  test("renders server failure feedback", async () => {
    mockPost.mockRejectedValue({ response: { data: { detail: "Please try again later." } } });
    const { container, cleanup } = mountHome();
    setInputValue(container.querySelector('[data-testid="newsletter-name"]'), "Reader Example");
    setInputValue(container.querySelector('[data-testid="newsletter-email"]'), "reader@example.test");
    await submitForm(container);
    expect(container.querySelector('#newsletter-status').textContent).toBe("Please try again later.");
    expect(mockToastError).toHaveBeenCalledWith("Please try again later.");
    cleanup();
  });

  test("analytics exceptions do not block the request or success feedback", async () => {
    mockTrackFunnelEvent.mockImplementation((event) => {
      if (event.startsWith("newsletter_submit_")) throw new Error("analytics unavailable");
    });
    const { container, cleanup } = mountHome();
    setInputValue(container.querySelector('[data-testid="newsletter-name"]'), "Reader Example");
    setInputValue(container.querySelector('[data-testid="newsletter-email"]'), "reader@example.test");
    await submitForm(container);
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(container.querySelector('#newsletter-status').textContent).toContain("Welcome to the Reading Circle");
    cleanup();
  });
});
