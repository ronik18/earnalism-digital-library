import { formatError, formatMinutes, resolveBackendUrl } from "./api";

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

  test("defaults production API traffic to same-origin when no explicit backend is configured", () => {
    const previousNodeEnv = process.env.NODE_ENV;
    const previousBackendUrl = process.env.REACT_APP_BACKEND_URL;
    const previousApiUrl = process.env.REACT_APP_API_URL;

    process.env.NODE_ENV = "production";
    delete process.env.REACT_APP_BACKEND_URL;
    delete process.env.REACT_APP_API_URL;

    try {
      expect(resolveBackendUrl()).toBe("");
    } finally {
      process.env.NODE_ENV = previousNodeEnv;
      if (previousBackendUrl === undefined) delete process.env.REACT_APP_BACKEND_URL;
      else process.env.REACT_APP_BACKEND_URL = previousBackendUrl;
      if (previousApiUrl === undefined) delete process.env.REACT_APP_API_URL;
      else process.env.REACT_APP_API_URL = previousApiUrl;
    }
  });

  test("rejects localhost production backend config and keeps same-origin API fallback", () => {
    const previousNodeEnv = process.env.NODE_ENV;
    const previousBackendUrl = process.env.REACT_APP_BACKEND_URL;

    process.env.NODE_ENV = "production";
    process.env.REACT_APP_BACKEND_URL = "http://localhost:8000";

    try {
      expect(resolveBackendUrl()).toBe("");
    } finally {
      process.env.NODE_ENV = previousNodeEnv;
      if (previousBackendUrl === undefined) delete process.env.REACT_APP_BACKEND_URL;
      else process.env.REACT_APP_BACKEND_URL = previousBackendUrl;
    }
  });
});
