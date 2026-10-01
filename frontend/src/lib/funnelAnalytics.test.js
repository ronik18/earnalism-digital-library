import {
  analyticsNetworkEnabled,
  classifyAnalyticsDeployment,
  classifyReferrer,
  createMockAnalyticsSink,
  getAnonymousLaunchSessionId,
  getLaunchAnalyticsAttribution,
  isUnsafeAnalyticsMetadataKey,
  resetLaunchAnalyticsForTests,
  setAnalyticsSink,
  trackFunnelEvent,
  trackPageAnalyticsView,
} from "./funnelAnalytics";

describe("first-party journey analytics", () => {
  beforeEach(() => {
    resetLaunchAnalyticsForTests();
    window.sessionStorage.clear();
    window.history.replaceState({}, "", "/");
    delete window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__;
  });

  test("deduplicates route views by navigation key and permits a later real navigation", () => {
    const sink = createMockAnalyticsSink();
    setAnalyticsSink(sink);
    trackPageAnalyticsView("homepage_view", "home-1", "/");
    trackPageAnalyticsView("homepage_view", "home-1", "/");
    trackPageAnalyticsView("homepage_view", "home-2", "/");
    trackPageAnalyticsView("homepage_view", "home-1", "/");
    expect(sink.events.map(({ event }) => event)).toEqual(["homepage_view", "homepage_view", "homepage_view"]);
  });

  test("supports required public route events without aliasing pricing into a legacy metric", () => {
    const sink = createMockAnalyticsSink();
    setAnalyticsSink(sink);
    ["homepage_view", "library_view", "title_view", "reader_preview_started", "pricing_view"].forEach((event) => trackFunnelEvent(event));
    expect(sink.events.map(({ event }) => event)).toEqual([
      "homepage_view", "library_view", "title_view", "reader_preview_started", "pricing_view",
    ]);
    expect(trackFunnelEvent("purchase_completed")).toBe(false);
  });

  test("uses tab-scoped anonymous identifiers and never includes authentication or payment fields", () => {
    const sink = createMockAnalyticsSink();
    setAnalyticsSink(sink);
    const sessionId = getAnonymousLaunchSessionId();
    trackFunnelEvent("checkout_failed", {
      reason: "gateway_error",
      customer_email: "reader@example.com",
      razorpay_payment_id: "pay_abcd1234567890",
      password: "should-not-appear",
    });
    expect(sessionId).toMatch(/^[a-z0-9-]{12,80}$/i);
    expect(window.sessionStorage.length).toBeGreaterThan(0);
    expect(sink.events[0].metadata).toEqual({ reason: "gateway_error" });
    expect(isUnsafeAnalyticsMetadataKey("authorization")).toBe(true);
  });

  test("captures only allowlisted UTMs and a coarse referrer category", () => {
    window.history.replaceState({}, "", "/?utm_source=reader-letter&utm_medium=email&utm_campaign=october&email=reader%40example.com");
    expect(getLaunchAnalyticsAttribution()).toEqual({
      utm_source: "reader-letter",
      utm_medium: "email",
      utm_campaign: "october",
      referrer_category: "campaign",
    });
    expect(classifyReferrer("https://www.google.co.in/search?q=earnalism")).toBe("organic");
    expect(classifyReferrer("")).toBe("direct");
  });

  test("separates production, preview, and local event environments", () => {
    expect(classifyAnalyticsDeployment("theearnalism.com")).toBe("production");
    expect(classifyAnalyticsDeployment("earnalism-git-branch.vercel.app")).toBe("preview");
    expect(classifyAnalyticsDeployment("127.0.0.1")).toBe("local");
  });

  test("disabled flag suppresses delivery and delivery exceptions fail open", () => {
    const originalFetch = global.fetch;
    const fetchSpy = jest.fn(() => { throw new Error("offline"); });
    global.fetch = fetchSpy;
    Object.defineProperty(navigator, "sendBeacon", { configurable: true, value: () => false });
    process.env.REACT_APP_ENABLE_LAUNCH_ANALYTICS = "false";
    expect(analyticsNetworkEnabled()).toBe(false);
    expect(() => trackFunnelEvent("homepage_view")).not.toThrow();
    expect(fetchSpy).not.toHaveBeenCalled();

    process.env.REACT_APP_ENABLE_LAUNCH_ANALYTICS = "true";
    expect(analyticsNetworkEnabled()).toBe(true);
    expect(() => trackFunnelEvent("library_view")).not.toThrow();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    global.fetch = originalFetch;
    delete process.env.REACT_APP_ENABLE_LAUNCH_ANALYTICS;
  });

  test("a throwing diagnostic sink cannot interrupt a product action", () => {
    setAnalyticsSink(() => { throw new Error("diagnostic sink unavailable"); });
    expect(() => trackFunnelEvent("signup_started", { source: "email_form" })).not.toThrow();
  });

  test("network payload keeps path and allowlisted attribution but strips query and forbidden PII", () => {
    const originalFetch = global.fetch;
    const fetchSpy = jest.fn(() => Promise.resolve({ ok: true }));
    global.fetch = fetchSpy;
    Object.defineProperty(navigator, "sendBeacon", { configurable: true, value: () => false });
    process.env.REACT_APP_ENABLE_LAUNCH_ANALYTICS = "true";
    window.history.replaceState({}, "", "/book/a-ghost-story?utm_source=reader-letter&email=reader%40example.com&next=%2Faccount");

    trackFunnelEvent("title_view", { book_slug: "a-ghost-story", customer_email: "reader@example.com" });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy.mock.calls[0][0]).toMatch(/\/api\/analytics\/event$/);
    const request = fetchSpy.mock.calls[0][1];
    expect(request.method).toBe("POST");
    const payload = JSON.parse(request.body);
    expect(payload.route).toBe("/book/a-ghost-story");
    expect(payload.deployment_environment).toBe("local");
    expect(payload.metadata.utm_source).toBe("reader-letter");
    expect(payload.metadata).not.toHaveProperty("customer_email");
    expect(JSON.stringify(payload)).not.toMatch(/reader@example\.com|next=|email=/);

    global.fetch = originalFetch;
    delete process.env.REACT_APP_ENABLE_LAUNCH_ANALYTICS;
  });
});
