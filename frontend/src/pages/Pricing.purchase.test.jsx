import React, { act } from "react";
import { createRoot } from "react-dom/client";
import Pricing from "./Pricing";
import { api, userApi } from "../lib/api";
import { toast } from "sonner";
import { trackFunnelEvent } from "../lib/funnelAnalytics";
let mockProps;
const mockRefreshUser = jest.fn();
const mockNavigate = jest.fn();
jest.mock("../lib/controlledLaunch", () => ({ PUBLIC_PAID_COMMERCE_ENABLED: true }));
jest.mock("../hooks/useSEO", () => () => {});
jest.mock("../context/AuthContext", () => ({ useAuth: () => ({ user: { id: "user" }, refreshUser: mockRefreshUser }) }));
jest.mock("react-router-dom", () => ({ Link: ({ children }) => children, useNavigate: () => mockNavigate, useSearchParams: () => [new URLSearchParams()] }), { virtual: true });
jest.mock("../components/ReadingPassesSurface", () => props => { mockProps = props; return null; });
jest.mock("../components/PublicPageFrame", () => ({ children }) => children);
jest.mock("../lib/api", () => ({ api: { get: jest.fn(async () => ({ data: { packs: [{ id: "1h", minutes: 60, price_inr: 89 }], config: { configured: true } } })) }, userApi: { post: jest.fn(), get: jest.fn() }, formatError: x => x }));
jest.mock("sonner", () => ({ toast: { success: jest.fn(), message: jest.fn(), error: jest.fn() } }));
jest.mock("../lib/funnelAnalytics", () => ({ trackFunnelEvent: jest.fn(), classifyAnalyticsDeployment: () => "uat", getAnonymousLaunchSessionId: () => "fixture", getLaunchAnalyticsAttribution: () => ({}) }));

test.each([
  ["failed verify with old receipt", true, { id: "old-intent", status: "credited" }, false],
  ["failed verify with matching receipt", true, { id: "new-intent", status: "credited" }, true],
  ["verified current receipt", false, { id: "new-intent", status: "credited" }, true],
  ["verified stale receipt", false, { id: "old-intent", status: "credited" }, false],
  ["verified pending receipt", false, { id: "new-intent", status: "created" }, false],
])("rendered checkout uses exact purchase evidence: %s", async (_label, verifyFails, receipt, credited) => {
  jest.clearAllMocks();
  global.IS_REACT_ACT_ENVIRONMENT = true;
  api.get.mockResolvedValue({ data: { packs: [{ id: "1h", minutes: 60, price_inr: 89 }], config: { configured: true } } });
  let options;
  window.Razorpay = function(opts) { options = opts; this.on = jest.fn(); this.open = jest.fn(); };
  mockRefreshUser.mockResolvedValue({ reading_seconds_balance: 7200 });
  userApi.post.mockImplementation(async url => {
    if (url === "/payments/topup") return { data: { intent_id: "new-intent", razorpay_order_id: "order_local" } };
    if (verifyFails) throw new Error("synthetic verify failure");
    return { data: { intent: receipt } };
  });
  userApi.get.mockResolvedValue({ data: [receipt] });
  const node = document.createElement("div"); const root = createRoot(node);
  await act(async () => root.render(<Pricing />));
  await act(async () => mockProps.onBuy({ id: "1h", minutes: 60 }));
  await act(async () => options.handler({ razorpay_order_id: "order_local", razorpay_payment_id: "pay_local", razorpay_signature: "synthetic" }));
  expect(trackFunnelEvent.mock.calls.some(([event]) => event === "wallet_credited_visible")).toBe(credited);
  if (credited) expect(toast.success).toHaveBeenCalledWith("+60 minutes added.");
  else {
    expect(toast.success).not.toHaveBeenCalledWith("+60 minutes added.");
    if (verifyFails) expect(toast.message).toHaveBeenCalled();
  }
  expect(mockNavigate).toHaveBeenCalledWith("/account");
  await act(async () => root.unmount());
});
