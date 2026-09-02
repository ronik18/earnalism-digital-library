export function isRequestCancellation(error) {
  return error?.name === "AbortError"
    || error?.name === "CanceledError"
    || error?.code === "ERR_CANCELED";
}
