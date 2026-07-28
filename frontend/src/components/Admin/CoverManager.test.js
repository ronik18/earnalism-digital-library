const fs = require("fs");
const path = require("path");

const adminSource = fs.readFileSync(path.join(process.cwd(), "src/pages/Admin.jsx"), "utf8");
const managerSource = fs.readFileSync(path.join(process.cwd(), "src/components/Admin/CoverManager.jsx"), "utf8");
const uploadSource = fs.readFileSync(path.join(process.cwd(), "src/components/Admin/CoverUpload.jsx"), "utf8");

describe("admin Sprint 1 cover desk", () => {
  test("exposes a dedicated authenticated admin cover workspace", () => {
    expect(adminSource).toContain('"covers"');
    expect(adminSource).toContain('tab === "covers"');
    expect(adminSource).toContain("<CoverManager />");
    expect(managerSource).toContain('api.get("/admin/books/cover-status")');
    expect(managerSource).toContain('data-testid="admin-cover-manager"');
  });

  test("shows canonical missing, pending, mismatch, and complete states", () => {
    expect(managerSource).toContain("CANONICAL_READY");
    expect(managerSource).toContain("MISSING");
    expect(managerSource).toContain("MISMATCH_REVIEW_REQUIRED");
    expect(managerSource).toContain("UPLOADED_PENDING_CANONICAL_REVIEW");
    expect(managerSource).toContain("reader availability or audiobook release state");
  });

  test("uploads through the shared admin client with explicit bounded-job confirmation", () => {
    expect(uploadSource).toContain('api.post(`/admin/books/${bookId}/cover`');
    expect(uploadSource).toContain("confirm_expensive_job: true");
    expect(uploadSource).toContain('"aria-label": `Upload ${label.toLowerCase()} image`');
    expect(uploadSource).toContain("Cover uploaded for canonical review.");
    expect(adminSource).toContain("setPendingCoverUrls");
    expect(adminSource).not.toContain("cover_image_url: data.cover_url");
    expect(adminSource).not.toContain("back_cover_image_url: data.cover_url");
    expect(uploadSource).not.toContain("axios.post");
    expect(uploadSource).not.toContain("TOKEN_KEY");
    expect(uploadSource).not.toContain("image/gif");
  });
});
