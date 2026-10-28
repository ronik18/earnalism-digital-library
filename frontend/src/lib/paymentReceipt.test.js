import { hasCreditedPurchase } from "./paymentReceipt";

test("pre-existing positive balance cannot confirm this purchase", () => {
  expect(hasCreditedPurchase({ reading_seconds_balance: 7200 }, "new-intent")).toBe(false);
  expect(hasCreditedPurchase({ id: "old-intent", status: "credited" }, "new-intent")).toBe(false);
  expect(hasCreditedPurchase(null, "new-intent")).toBe(false);
});
test("requires exact credited intent even during wallet spending", () => {
  expect(hasCreditedPurchase({ id: "new-intent", status: "created", reading_seconds_balance: 7200 }, "new-intent")).toBe(false);
  expect(hasCreditedPurchase({ id: "new-intent", status: "credited", reading_seconds_balance: 0 }, "new-intent")).toBe(true);
});
