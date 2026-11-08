import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { Privacy, Terms } from "./LegalPages";

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}), { virtual: true });
jest.mock("../components/PublicPageFrame", () => ({ children }) => <div>{children}</div>);
jest.mock("../hooks/useSEO", () => jest.fn());

describe("accepted named operator notice", () => {
  let host;
  let root;
  beforeEach(() => {
    global.IS_REACT_ACT_ENVIRONMENT = true;
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
  });
  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });
  test("Terms gives an honest purchase pause and direct cancellation paths", () => {
    act(() => root.render(<Terms />));
    expect(host.textContent).toContain("New Reading Pass purchases are temporarily paused");
    expect(host.textContent).toContain("Merely starting to read does not constitute a blanket waiver");
    expect(host.textContent).toContain("There is no subscription or automatic renewal");
    expect(host.querySelector('a[href="/cancellation-form.txt"]').hasAttribute("download")).toBe(true);
    expect(host.querySelector('a[href^="mailto:sales@reoenterprise.org?subject="]')).not.toBeNull();
  });
  test.each([["Privacy", Privacy], ["Terms", Terms]])("%s renders the accepted contact and request paths", (_name, Page) => {
    act(() => root.render(<Page />));
    expect(host.textContent).toContain("Grievance Officer and privacy/support contact: Ronik Basak");
    expect(host.textContent).toContain("Earnalism (operated by REO ENTERPRISE)");
    expect(host.textContent).toContain("Nihar Bhawan, 73 Nandan Nagar, Kolkata 700083, North 24 Parganas, West Bengal, India");
    expect(host.querySelector('a[href="mailto:sales@reoenterprise.org"]')).not.toBeNull();
    expect(host.querySelector('a[href="/contact?intent=reader"]')).not.toBeNull();
    expect(host.querySelector('a[href="/contact?intent=rights"]')).not.toBeNull();
  });
});
