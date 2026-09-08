export function listenerRecoveryPlan({ error = "" } = {}) {
  const accessMessage = String(error || "").toLowerCase();
  const releaseUnavailable = /not enabled|disabled|unavailable|not approved/.test(accessMessage);
  return {
    needsPass: !releaseUnavailable && /current reading pass|required to listen|lease|authorization expired/.test(accessMessage),
  };
}
