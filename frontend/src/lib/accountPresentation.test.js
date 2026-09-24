import { formatSessionDeviceLabel, formatSessionLastActive, sortSessionDevices } from "./accountPresentation";

describe("account session presentation", () => {
  test.each([
    ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36", "Chrome on Mac"],
    ["Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1", "Safari on iPhone"],
    ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0", "Edge on Windows"],
    ["MacIntel · Browser", "Browser on Mac"],
    ["Web · Mobile", "Mobile browser"],
    ["curl/8.4.0", "Browser"],
    ["", "Browser"],
  ])("formats %s as %s", (value, expected) => {
    expect(formatSessionDeviceLabel(value)).toBe(expected);
  });

  test("keeps the current and active sessions ahead of historical sessions", () => {
    const rows = [
      { session_id: "revoked", status: "revoked", last_seen_at: "2026-09-22T12:00:00Z" },
      { session_id: "other-active", status: "active", last_seen_at: "2026-09-23T12:00:00Z" },
      { session_id: "current", status: "active", current: true, last_seen_at: "2026-09-22T10:00:00Z" },
    ];
    expect(sortSessionDevices(rows).map((row) => row.session_id)).toEqual(["current", "other-active", "revoked"]);
  });

  test("formats valid activity timestamps and hides invalid values", () => {
    expect(formatSessionLastActive("not-a-date")).toBe("");
    expect(formatSessionLastActive("2026-09-23T10:00:00Z")).not.toBe("");
  });
});
