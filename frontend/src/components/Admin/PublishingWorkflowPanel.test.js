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

test("admin panel displays all blockers and separate unverified capabilities", () => {
  const html = renderToStaticMarkup(<PublishingWorkflowPanel book={{ slug: "unknown-book", is_published: true }} />);
  expect(html).toContain("Rights approval is required.");
  expect(html).toContain("BLOCKED_INGESTION");
  expect(html).toContain("Protected-text authority");
  expect(html).toContain("End-to-end acceptance");
  expect(html.match(/UNVERIFIED · No authoritative reporting value supplied/g)).toHaveLength(6);
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
