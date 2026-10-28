// A wallet balance can predate checkout; only this purchase's receipt proves credit.
export const hasCreditedPurchase = (intent, intentId) =>
  Boolean(intentId && intent?.id === intentId && intent?.status === "credited");
