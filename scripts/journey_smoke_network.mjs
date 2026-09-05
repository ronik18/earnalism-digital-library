export function isHardSmokeNetworkFailure(item) {
  if (item.status >= 500) return true;
  if (item.type !== "requestfailed") return false;

  // Chromium reports ERR_ABORTED when the client intentionally supersedes an
  // in-flight request during navigation. That is not evidence of a network or
  // server failure; route status/error checks cover failed navigations.
  const failureText = String(item.failure || "").toLowerCase();
  if (failureText.includes("err_aborted") || failureText === "aborted") return false;

  return ["document", "fetch", "xhr", "script"].includes(item.resource_type);
}
