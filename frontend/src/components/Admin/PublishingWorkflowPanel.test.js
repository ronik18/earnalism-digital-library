import { renderToStaticMarkup } from "react-dom/server";
import PublishingWorkflowPanel, { derivePublishingWorkflow } from "./PublishingWorkflowPanel";

test("admin workflow reads canonical fields before legacy aliases", () => {
  const workflow = derivePublishingWorkflow({
    slug: "canonical-book",
    rights_metadata: { rights_tier: "B", verification_status: "APPROVED" },
    action_status: "",
    publication_workflow: {
      rights: { tier: "A", verification_status: "APPROVED", blocked_reason: "" },
      demand: { score: 90, action_status: "READY_FOR_GENERATION" },
      ingestion: { status: "CLEANED" },
      edition: { status: "QA_PASSED" },
      visual: { status: "QA_PASSED" },
      audio: { status: "AUDIO_NOT_REQUIRED" },
      qa: { status: "QA_PASSED", warnings: [] },
      cost: { used: 0, budget: 10 },
      publication: { state: "READY_FOR_PUBLICATION", reader_exposed: false, audio_exposed: false },
    },
  });

  expect(workflow.sections["rights status"]).toBe("A APPROVED");
  expect(workflow.publishReadiness).toBe("READY");
});

const reportingBook = (workflow, status = "RECORDED") => ({
  slug: "reporting-book",
  is_published: true,
  publication_workflow: workflow,
  admin_reporting: {
    workflow: { status, source: "validated stored publication_workflow" },
    editorial: { status: "PUBLISHED", source: "stored is_published" },
    preview: { status: "CONFIGURED_AVAILABLE", source: "runtime configuration" },
    protected_text: { status: "UNVERIFIED", source: "not inspected" },
    acceptance: { status: "UNVERIFIED", source: "no acceptance receipt" },
  },
});

const recordedWorkflow = (rights) => ({
  schema_name: "earnalism-publication-workflow",
  schema_version: 2,
  rights,
  demand: { action_status: "READY_FOR_GENERATION" },
  ingestion: { status: "CLEANED" },
  edition: { status: "QA_PASSED" },
  visual: { status: "QA_PASSED" },
  audio: { status: "AUDIO_NOT_REQUIRED" },
  qa: { status: "QA_PASSED" },
  cost: { used: 0, budget: 10 },
  publication: { state: "DRAFT" },
});

test.each([
  ["missing", null],
  ["malformed", { rights: { verification_status: "APPROVED" } }],
])("%s workflow evidence renders unavailable, not a rights decision", (_label, workflow) => {
  const html = renderToStaticMarkup(<PublishingWorkflowPanel book={reportingBook(workflow, "UNAVAILABLE")} />);
  expect(html).toContain("Workflow evidence unavailable");
  expect(html).toContain("Publication readiness cannot be assessed because workflow evidence is missing or invalid.");
  expect(html).toContain("UNAVAILABLE");
  expect(html).not.toContain("RIGHTS PENDING");
  expect(html).not.toContain("Rights approval is required.");
  expect(html).not.toContain("READY_FOR_PUBLICATION");
  expect(html).not.toContain(">READY<");
  expect(html).not.toContain(">BLOCKED<");
  expect(html).not.toContain("BLOCKED_INGESTION");
  expect(html).toContain("Protected-text authority");
  expect(html).toContain("End-to-end acceptance");
  expect(html).toContain("UNVERIFIED · no acceptance receipt");
  expect(html.match(/disabled=""/g)).toHaveLength(2);
});

test("missing availability discriminator never falls back to an inferred rights decision", () => {
  const html = renderToStaticMarkup(<PublishingWorkflowPanel book={{ slug: "unknown-book", is_published: true }} />);
  expect(html).toContain("Workflow evidence unavailable");
  expect(html).not.toContain("Rights approval is required.");
  expect(html).toContain("UNAVAILABLE");
});

test("valid pending rights evidence retains its actual explanation", () => {
  const workflow = recordedWorkflow({ tier: "A", verification_status: "PENDING" });
  const html = renderToStaticMarkup(<PublishingWorkflowPanel book={reportingBook(workflow)} />);
  expect(html).toContain("RIGHTS PENDING");
  expect(html).toContain("Rights verification must be approved.");
  expect(html).not.toContain("Workflow evidence unavailable");
});

test("valid denied rights evidence retains the existing quarantine and denial explanation", () => {
  const workflow = recordedWorkflow({ tier: "C", verification_status: "DENIED", blocked_reason: "Rights denied" });
  const html = renderToStaticMarkup(<PublishingWorkflowPanel book={reportingBook(workflow)} />);
  expect(html).toContain("QUARANTINED");
  expect(html).toContain("BLOCKED_RIGHTS: Tier C cannot publish anywhere.");
  expect(html).toContain("Rights blocked reason must be cleared.");
  expect(html).not.toContain("Workflow evidence unavailable");
});

test("valid workflow renders every evaluator blocker and keeps acceptance separate", () => {
  const workflow = recordedWorkflow({ tier: "A", verification_status: "PENDING" });
  workflow.ingestion.status = "MISSING";
  workflow.edition.status = "MISSING";
  const book = reportingBook(workflow);
  const html = renderToStaticMarkup(<PublishingWorkflowPanel book={book} />);
  const blockers = derivePublishingWorkflow(book).blockers;
  expect(blockers.length).toBeGreaterThan(1);
  blockers.forEach((blocker) => expect(html).toContain(blocker));
  expect(html).toContain("PUBLISHED · stored is_published");
  expect(html).toContain("CONFIGURED_AVAILABLE · runtime configuration");
  expect(html).toContain("UNVERIFIED · no acceptance receipt");
});

test("published records retain independent missing-evidence blockers", () => {
  const workflow = derivePublishingWorkflow({
    slug: "published-book",
    is_published: true,
    publication_workflow: {
      publication: { state: "PUBLISHED", reader_exposed: true, audio_exposed: false },
    },
  });

  expect(workflow.state).toBe("PUBLISHED");
  expect(workflow.publishReadiness).toBe("PUBLISHED");
  expect(workflow.blockers).toContain("Rights approval is required.");
  expect(workflow.blockers).toContain("BLOCKED_PRIORITY_GATE: Phase 3 action_status must be READY_FOR_GENERATION.");
});
