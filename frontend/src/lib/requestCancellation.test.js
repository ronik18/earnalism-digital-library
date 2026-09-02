import { isRequestCancellation } from "./requestCancellation";

describe("request cancellation", () => {
  test.each([
    [{ name: "AbortError" }],
    [{ name: "CanceledError" }],
    [{ code: "ERR_CANCELED" }],
  ])("recognizes cancelled request errors: %o", (error) => {
    expect(isRequestCancellation(error)).toBe(true);
  });

  test("does not suppress a real request failure", () => {
    expect(isRequestCancellation({ name: "NetworkError" })).toBe(false);
  });
});
