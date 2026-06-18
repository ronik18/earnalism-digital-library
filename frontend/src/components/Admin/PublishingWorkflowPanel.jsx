const SECTION_LABELS = [
  "rights status",
  "demand score",
  "ingestion status",
  "edition generation status",
  "visual status",
  "audio status",
  "QA warnings",
  "cost used",
  "publish readiness",
];

const ALLOWED_INGESTION_STATUSES = new Set(["INGESTED", "CLEANED"]);
const ALLOWED_GENERATION_STATUSES = new Set(["READY_FOR_REVIEW", "PARTIAL_DRY_RUN", "QA_PASSED"]);
const ALLOWED_AUDIO_STATUSES = new Set(["DRY_RUN_READY", "READY_FOR_REVIEW", "QA_PASSED", "AUDIO_NOT_REQUIRED"]);

function normalizeStatus(value) {
  return String(value || "").trim().toUpperCase().replace(/[-\s]+/g, "_");
}

function rightsMetadata(book) {
  return book?.rights_metadata && typeof book.rights_metadata === "object" ? book.rights_metadata : {};
}

export function derivePublishingWorkflow(book = {}) {
  const report = book.publishing_workflow_report || book.workflow_report;
  if (report && typeof report === "object") {
    return workflowFromReport(report);
  }

  const rights = rightsMetadata(book);
  const workflow = book.publishing_workflow && typeof book.publishing_workflow === "object" ? book.publishing_workflow : {};
  const demand = book.demand && typeof book.demand === "object" ? book.demand : {};
  const qa = book.qa && typeof book.qa === "object" ? book.qa : {};
  const cost = book.cost && typeof book.cost === "object" ? book.cost : {};

  const rightsTier = normalizeStatus(rights.rights_tier || book.rights_tier);
  const verificationStatus = normalizeStatus(rights.verification_status || book.verification_status);
  const qaStatus = normalizeStatus(qa.qa_status || book.qa_status);
  const actionStatus = normalizeStatus(demand.action_status || book.action_status);
  const ingestionStatus = normalizeStatus(book.ingestion_status || workflow.ingestion_status);
  const editionStatus = normalizeStatus(book.edition_generation_status || workflow.edition_generation_status);
  const visualStatus = normalizeStatus(book.visual_status || workflow.visual_status);
  const audioStatus = normalizeStatus(book.audio_status || workflow.audio_status);
  const costUsed = Number(cost.used || book.cost_used || 0);
  const costBudget = Number(cost.budget || book.cost_budget || 0);
  const blockers = [];

  if (rightsTier === "C") blockers.push("BLOCKED_RIGHTS: Tier C cannot publish anywhere.");
  if (rightsTier === "B") blockers.push("REGION_GATED_REVIEW: Tier B is not eligible for normal global publication.");
  if (!["A", "B", "C"].includes(rightsTier)) blockers.push("Rights approval is required.");
  if (rightsTier === "A" && verificationStatus !== "APPROVED") blockers.push("Rights verification must be approved.");
  if (rights.blocked_reason || book.blocked_reason) blockers.push("Rights blocked reason must be cleared.");
  if (actionStatus !== "READY_FOR_GENERATION") blockers.push("BLOCKED_PRIORITY_GATE: Phase 3 action_status must be READY_FOR_GENERATION.");
  if (!ALLOWED_INGESTION_STATUSES.has(ingestionStatus)) blockers.push("BLOCKED_INGESTION: Phase 4 ingestion_status must be INGESTED or CLEANED.");
  if (!ALLOWED_GENERATION_STATUSES.has(editionStatus)) blockers.push("BLOCKED_EDITION_GATE: Phase 5 edition_generation_status must be ready, partial dry-run, or QA passed.");
  if (!ALLOWED_GENERATION_STATUSES.has(visualStatus)) blockers.push("BLOCKED_VISUAL_GATE: Phase 6 visual_status must be ready, partial dry-run, or QA passed.");
  if (!ALLOWED_AUDIO_STATUSES.has(audioStatus)) blockers.push("BLOCKED_AUDIO_GATE: Phase 7 audio_status must be ready, QA passed, or AUDIO_NOT_REQUIRED.");
  if (qaStatus !== "QA_PASSED") blockers.push("QA pass is required.");
  if (costBudget > 0 && costUsed > costBudget) blockers.push("BLOCKED_COST: Cost budget is exceeded.");

  let state = "DISCOVERED";
  if (workflow.archived || book.archived) state = "ARCHIVED";
  else if (workflow.quarantined || book.quarantined || rightsTier === "C" || rights.blocked_reason) state = "QUARANTINED";
  else if (workflow.paused || book.paused) state = "PAUSED";
  else if (book.is_published) state = "PUBLISHED";
  else if (blockers.length && blockers.some((item) => /rights|tier/i.test(item))) state = "RIGHTS_PENDING";
  else if (blockers.length && blockers.some((item) => /priority/i.test(item))) state = "DEMAND_SCORED";
  else if (blockers.length && blockers.some((item) => /ingestion/i.test(item))) state = ingestionStatus === "INGESTED" ? "INGESTED" : "RIGHTS_APPROVED";
  else if (blockers.length && blockers.some((item) => /edition/i.test(item))) state = "CLEANED";
  else if (blockers.length && blockers.some((item) => /visual/i.test(item))) state = "EDITION_GENERATED";
  else if (blockers.length && blockers.some((item) => /audio/i.test(item))) state = "VISUALS_GENERATED";
  else if (blockers.length && blockers.some((item) => /qa|cost/i.test(item))) state = "QA_PENDING";
  else if (qaStatus === "QA_PASSED") state = "READY_FOR_PUBLICATION";
  else if (qaStatus) state = "QA_PENDING";
  else if (audioStatus) state = "AUDIO_PREVIEW_GENERATED";
  else if (visualStatus) state = "VISUALS_GENERATED";
  else if (editionStatus) state = "EDITION_GENERATED";
  else if (ingestionStatus === "CLEANED") state = "CLEANED";
  else if (ingestionStatus === "INGESTED") state = "INGESTED";
  else if (actionStatus) state = "DEMAND_SCORED";
  else if (rightsTier === "A" && ["APPROVED", "VERIFIED"].includes(verificationStatus)) state = "RIGHTS_APPROVED";

  const publishReadiness = blockers.some((item) => item.includes("REGION_GATED_REVIEW"))
    ? "REGION_GATED_REVIEW"
    : state === "READY_FOR_PUBLICATION" && blockers.length === 0
      ? "READY"
      : state === "PUBLISHED"
        ? "PUBLISHED"
        : "BLOCKED";
  return {
    state,
    publishReadiness,
    blockers,
    sections: {
      "rights status": `${rightsTier || "UNKNOWN"} ${verificationStatus || ""}`.trim(),
      "demand score": demand.demand_score || book.demand_score || "not scored",
      "ingestion status": ingestionStatus || "missing",
      "edition generation status": editionStatus || "missing",
      "visual status": visualStatus || "missing",
      "audio status": audioStatus || "missing",
      "QA warnings": (qa.warnings || book.qa_warnings || []).length,
      "cost used": costBudget ? `${costUsed}/${costBudget}` : costUsed,
      "publish readiness": publishReadiness,
    },
    rollbackAvailable: ["READY_FOR_PUBLICATION", "PUBLISHED", "PAUSED"].includes(state),
    pauseAvailable: !["ARCHIVED", "QUARANTINED"].includes(state),
  };
}

function workflowFromReport(report) {
  const sections = {};
  (report.dashboard_sections || []).forEach((section) => {
    if (section?.section) sections[section.section] = section.value ?? section.status ?? "missing";
  });
  SECTION_LABELS.forEach((label) => {
    if (!(label in sections)) sections[label] = "missing";
  });
  sections["publish readiness"] = report.publish_readiness || sections["publish readiness"];
  return {
    state: normalizeStatus(report.state || "DISCOVERED"),
    publishReadiness: normalizeStatus(report.publish_readiness || "BLOCKED"),
    blockers: Array.isArray(report.blockers) ? report.blockers : [],
    sections,
    rollbackAvailable: Boolean(report.dry_run_publication?.rollback_plan?.length),
    pauseAvailable: !["ARCHIVED", "QUARANTINED"].includes(normalizeStatus(report.state)),
  };
}

export default function PublishingWorkflowPanel({ book }) {
  const workflow = derivePublishingWorkflow(book);
  return (
    <div className="mt-4 rounded-lg border border-brand-soft bg-white/50 p-3" data-testid={`publishing-workflow-${book.slug}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-[0.62rem] uppercase tracking-[0.18em] text-charcoal-soft">Publishing workflow · read-only dry-run estimate</div>
          <div className="font-serif-display text-lg text-burgundy">{workflow.state.replace(/_/g, " ")}</div>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-[0.6rem] uppercase tracking-[0.16em] ${workflow.publishReadiness === "READY" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
          {workflow.publishReadiness}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-charcoal-soft">
        {SECTION_LABELS.map((label) => (
          <div key={label} className="flex justify-between gap-2 border-b border-brand/40 pb-1">
            <span>{label}</span>
            <span className="text-right text-burgundy">{String(workflow.sections[label])}</span>
          </div>
        ))}
      </div>
      {workflow.blockers.length > 0 && (
        <ul className="mt-3 list-disc pl-4 text-xs text-amber-800">
          {workflow.blockers.slice(0, 3).map((blocker) => <li key={blocker}>{blocker}</li>)}
        </ul>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" disabled className="rounded-full border border-brand-soft px-3 py-1 text-[0.62rem] uppercase tracking-[0.16em] text-charcoal-soft opacity-70">
          Rollback dry-run
        </button>
        <button type="button" disabled className="rounded-full border border-brand-soft px-3 py-1 text-[0.62rem] uppercase tracking-[0.16em] text-charcoal-soft opacity-70">
          Pause dry-run
        </button>
      </div>
    </div>
  );
}
