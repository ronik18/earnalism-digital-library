const fs = require("fs");
const path = require("path");

const adminSource = fs.readFileSync(path.join(process.cwd(), "src/pages/Admin.jsx"), "utf8");
const inspectorSource = adminSource.split("export function PublicationInspectionAdmin()", 2)[1].split("function SimpleList", 2)[0];

describe("Yugalanguriya publication inspector", () => {
  test("is an explicit-action admin control using the shared authenticated client", () => {
    expect(adminSource).toContain('"publication-inspection"');
    expect(adminSource).toContain('tab === "publication-inspection"');
    expect(inspectorSource).toContain('api.get("/admin/reading-pass/yugalanguriya/publication-inspection")');
    expect(inspectorSource).toContain('data-testid="publication-inspection-run"');
    expect(inspectorSource).not.toContain("useEffect(() => { inspect();");
  });

  test("does not render raw errors, configs, or injected HTML", () => {
    expect(inspectorSource).toContain("No inspection has been run in this browser session.");
    expect(inspectorSource).toContain("No result has been inferred.");
    expect(inspectorSource).not.toContain("dangerouslySetInnerHTML");
    expect(inspectorSource).not.toContain("err.response?.data?.detail");
  });
});
