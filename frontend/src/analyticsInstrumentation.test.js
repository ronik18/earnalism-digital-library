import fs from "fs";
import path from "path";

const source = (file) => fs.readFileSync(path.join(process.cwd(), file), "utf8");

describe("route and conversion event ownership", () => {
  test("route tracker covers home, library, and pricing, while title views require a loaded matching book", () => {
    const app = source("src/App.js");
    const detail = source("src/pages/BookDetail.jsx");
    expect(app).toContain('"/": "homepage_view"');
    expect(app).toContain('"/library": "library_view"');
    expect(app).toContain('"/pricing": "pricing_view"');
    expect(detail).toContain('trackPageAnalyticsView("title_view"');
    expect(detail).toContain("book?.slug === slug");
  });

  test("Reader preview start is bound to a validated preview page, not a CTA click", () => {
    const reader = source("src/experiences-v2/reader/ReaderExperienceV2Route.jsx");
    expect(reader).toContain('trackFunnelEvent("reader_preview_started"');
    expect(reader).toContain("selectedPage.is_preview !== true");
    expect(reader).toContain("previewEventSentRef.current");
  });

  test("checkout start belongs to a created server order and purchase is never client-emitted", () => {
    const pricing = source("src/pages/Pricing.jsx");
    const backend = fs.readFileSync(path.resolve(process.cwd(), "../backend/server.py"), "utf8");
    expect(pricing).not.toContain('trackFunnelEvent("checkout_started"');
    expect(pricing).not.toContain('trackFunnelEvent("purchase_completed"');
    expect(backend).toContain('"checkout_started"');
    expect(backend).toContain('"purchase_completed"');
    expect(backend).toContain("Purchase completion is recorded only by verified server-side payment flows");
  });

  test("signup attempt and successful response have distinct PII-free events", () => {
    const signup = source("src/pages/Signup.jsx");
    expect(signup).toContain('trackFunnelEvent("signup_started", { source: "email_form" })');
    expect(signup).toContain('trackFunnelEvent("signup_completed", { source: "email_form" })');
    expect(signup).not.toContain("trackFunnelEvent(\"signup_completed\", { email");
    expect(signup.indexOf('trackFunnelEvent("signup_started"')).toBeLessThan(signup.indexOf("await userSignup("));
    expect(signup.indexOf('trackFunnelEvent("signup_completed"')).toBeGreaterThan(signup.indexOf("await userSignup("));
    expect(signup.indexOf('trackFunnelEvent("signup_completed"')).toBeLessThan(signup.indexOf("} catch (err)"));

    const login = source("src/pages/Login.jsx");
    expect(login).toContain('trackFunnelEvent("signin_started", { source: "email_form" })');
    expect(login).toContain('trackFunnelEvent("signin_completed", { source: "email_form" })');
    expect(login.lastIndexOf('trackFunnelEvent("signin_completed"')).toBeGreaterThan(login.indexOf("await userLogin("));
    expect(login.lastIndexOf('trackFunnelEvent("signin_completed"')).toBeLessThan(login.lastIndexOf("} catch (err)"));
  });
});
