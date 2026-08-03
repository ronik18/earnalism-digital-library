import { derivePublishingWorkflow } from "./PublishingWorkflowPanel";

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

test("published records do not display missing pre-publication blockers", () => {
  const workflow = derivePublishingWorkflow({
    slug: "published-book",
    is_published: true,
    publication_workflow: {
      publication: { state: "PUBLISHED", reader_exposed: true, audio_exposed: false },
    },
  });

  expect(workflow.state).toBe("PUBLISHED");
  expect(workflow.publishReadiness).toBe("PUBLISHED");
  expect(workflow.blockers).not.toContain("Rights approval is required.");
  expect(workflow.blockers).not.toContain("BLOCKED_PRIORITY_GATE: Phase 3 action_status must be READY_FOR_GENERATION.");
});
