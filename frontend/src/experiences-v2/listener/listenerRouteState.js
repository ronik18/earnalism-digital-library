export function listenerRecoveryPlan({ error = "" } = {}) {
  const accessMessage = String(error || "").toLowerCase();
  return {
    needsPass: /reading pass|lease|authorization expired|listen/.test(accessMessage),
  };
}
