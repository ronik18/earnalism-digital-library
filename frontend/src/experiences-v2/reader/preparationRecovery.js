// Timing advice only: the normal server admission and lease checks still apply.
export function preparationRetrySeconds(error) {
  const detail = error?.response?.data?.detail;
  const seconds = detail?.retry_after_seconds;
  return error?.response?.status === 403 && detail?.code === 'PREPARATION_EXPIRED'
    && Number.isSafeInteger(seconds) && seconds >= 0 && seconds <= 120 ? seconds : null;
}
