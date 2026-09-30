import fs from "fs";
import path from "path";
import { PUBLIC_AUDIO_EXPOSURE_ENABLED, PUBLIC_READER_RELEASED_SLUGS } from "./controlledLaunch";
import { bookDetailPresentationForBook } from "./bookDetailPresentation";

const repositoryRoot = path.resolve(__dirname, "../../..");
const controlledRoot = path.join(repositoryRoot, "data", "controlled_publications");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

describe("frontend release mirror", () => {
  test("exactly mirrors the canonical controlled-launch reader allowlist and release manifests", () => {
    const launch = readJson(path.join(repositoryRoot, "data", "controlled_launch.json"));
    const exclusions = readJson(path.join(repositoryRoot, "data", "catalog_exclusions.json")).titles || {};
    expect(PUBLIC_READER_RELEASED_SLUGS).toEqual(launch.live_approved_slugs);
    expect(PUBLIC_AUDIO_EXPOSURE_ENABLED).toBe(launch.public_audio_exposure_enabled);

    for (const slug of launch.live_approved_slugs) {
      expect(exclusions[slug]?.public_catalog_excluded).not.toBe(true);
      const packagePath = path.join(controlledRoot, slug);
      const publication = readJson(path.join(packagePath, "publication_manifest.json"));
      const publicBook = readJson(path.join(packagePath, "public_book.json"));
      const readerManifest = readJson(path.join(packagePath, "reader_manifest.json"));
      const rightsDecision = readJson(path.join(packagePath, "rights_decision.json"));

      expect(publication.slug).toBe(slug);
      expect(publication.rights.status).toBe("APPROVED");
      expect(publication.reader_release).toMatchObject({ status: "APPROVED", exposed: true });
      expect(publication.audio_release).toMatchObject({ status: "NOT_REQUESTED", exposed: false, required_for_reader_release: false });
      expect(publicBook.slug).toBe(slug);
      expect(publicBook.publication_status).toBe("LIVE_APPROVED");
      expect(readerManifest.slug).toBe(slug);
      expect(rightsDecision.status).toBe("ACCEPTED");
    }
  });

  test("A Ghost Story's canonical public package carries no audio release or playable asset", () => {
    const publicBook = readJson(path.join(controlledRoot, "a-ghost-story", "public_book.json"));
    const publication = readJson(path.join(controlledRoot, "a-ghost-story", "publication_manifest.json"));

    expect(publicBook).toMatchObject({ audio_enabled: false, audiobook_enabled: false, audiobook_assets: {} });
    expect(publication.audio_release).toMatchObject({ status: "NOT_REQUESTED", exposed: false, required_for_reader_release: false });
  });

  test("canonical publication approval alone does not bypass the runtime Reader manifest gate", () => {
    const publicBook = readJson(path.join(controlledRoot, "a-ghost-story", "public_book.json"));
    const presentation = bookDetailPresentationForBook({
      ...publicBook,
      _readerManifest: { slug: "a-ghost-story", audio: { enabled: false, assets: {} } },
    });

    expect(PUBLIC_READER_RELEASED_SLUGS).toContain("a-ghost-story");
    expect(presentation).toMatchObject({
      readerReady: true,
      readerRuntimeAvailable: false,
      readerStateLabel: "Reader currently unavailable",
      primaryReadLabel: "Browse the Library",
      primaryReadHref: "/library",
      listenCtaVisible: false,
    });
  });
});
