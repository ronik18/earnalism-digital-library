import fs from "fs";
import path from "path";
import { bookCoverImageSources } from "./images";

const repoRoot = path.resolve(process.cwd(), "..");
const packageRoot = path.join(
  repoRoot,
  "internal/audiobook_lab/sprint1_publication/cover_candidates/a-ghost-story/p0_v1",
);
const plan = JSON.parse(fs.readFileSync(
  path.join(packageRoot, "a-ghost-story-cover-assignment-plan.json"),
  "utf8",
));

const proposedBook = {
  slug: "a-ghost-story",
  title: "A Ghost Story",
  author: "Mark Twain",
  cover_url: plan.staged_media.front.immutable_url,
  cover_image_url: plan.staged_media.front.immutable_url,
  coverImage: plan.staged_media.front.immutable_url,
  cover_image: plan.staged_media.front.immutable_url,
  thumbnail_url: plan.staged_media.front.thumbnail_url,
  blur_placeholder: plan.staged_media.front.blur_placeholder,
  dominant_color: plan.staged_media.front.dominant_color,
  back_cover_url: plan.staged_media.back.immutable_url,
  back_cover_image_url: plan.staged_media.back.immutable_url,
  backCoverImage: plan.staged_media.back.immutable_url,
  back_cover_thumbnail_url: plan.staged_media.back.thumbnail_url,
  back_cover_blur_placeholder: plan.staged_media.back.blur_placeholder,
  back_cover_dominant_color: plan.staged_media.back.dominant_color,
};

describe("A Ghost Story proposed cover assignment component contract", () => {
  test("resolves the approved front and back staged metadata without the Bharat artwork", () => {
    const front = bookCoverImageSources(proposedBook, { width: 320, widths: [240, 320, 420] });
    const back = bookCoverImageSources(proposedBook, { kind: "back", width: 320, widths: [240, 320, 420] });

    for (const source of [front, back]) {
      expect(source.hasCover).toBe(true);
      expect(source.src).toContain("candidate_controlled-a-ghost-story");
      expect(source.srcSet).toContain("candidate_controlled-a-ghost-story");
      expect(source.src).not.toContain("446c5658-2bdd-4bd6-afbe-f5233f280508");
    }
    expect(front.placeholder).toContain("e_blur:2000");
    expect(front.backgroundColor).toBe("#161819");
    expect(back.placeholder).toContain("e_blur:2000");
    expect(back.backgroundColor).toBe("#101417");
  });

  test("keeps Library, Book Detail, and Listener surfaces on the shared cover component", () => {
    const sources = [
      "src/components/BookCard.jsx",
      "src/pages/BookDetail.jsx",
      "src/experiences-v2/listener/ListenerExperienceV2.jsx",
    ].map((relativePath) => fs.readFileSync(path.join(process.cwd(), relativePath), "utf8"));

    for (const source of sources) {
      expect(source).toContain('import BookCoverImage');
      expect(source).toContain("<BookCoverImage");
    }
    expect(sources[2]).toContain("allowGraphicalFallback={false}");
  });
});
