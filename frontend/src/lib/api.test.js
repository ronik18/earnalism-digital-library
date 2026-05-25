import { formatError, formatMinutes } from "./api";

describe("API display helpers", () => {
  test("formats API validation and detail errors for readers", () => {
    expect(formatError("No reading time left")).toBe("No reading time left");
    expect(formatError([{ msg: "Email is required" }, { msg: "Password is required" }]))
      .toBe("Email is required Password is required");
    expect(formatError(null)).toBe("Something went wrong. Please try again.");
  });

  test("formats wallet seconds into stable reading-time labels", () => {
    expect(formatMinutes(0)).toBe("0s");
    expect(formatMinutes(59)).toBe("59s");
    expect(formatMinutes(61)).toBe("1m 01s");
    expect(formatMinutes(3661)).toBe("1h 01m");
  });
});
