import { geometryAudit } from "./homeShelfGeometry";

test("wide Love/Duo card reserves a non-intersecting cover stage", () => {
  const audit = geometryAudit({ width: 560, height: 410 });
  expect(audit.intersection_count).toBe(0);
  expect(audit.outside_count).toBe(0);
});

test("narrow cards remain bounded", () => {
  const audit = geometryAudit({ width: 360, height: 390, coverRatio: 0.36 });
  expect(audit.intersection_count).toBe(0);
  expect(audit.outside_count).toBe(0);
});
