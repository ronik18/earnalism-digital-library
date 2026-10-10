const SECTION_LABELS = [
  "rights status",
  "content status",
  "reader release",
  "audio release",
];

const ALLOWED_INGESTION_STATUSES = new Set(["INGESTED", "CLEANED"]);
const ALLOWED_GENERATION_STATUSES = new Set(["READY_FOR_REVIEW", "PARTIAL_DRY_RUN", "QA_PASSED"]);
const ALLOWED_AUDIO_STATUSES = new Set(["DRY_RUN_READY", "READY_FOR_REVIEW", "QA_PASSED", "AUDIO_NOT_REQUIRED", "NOT_REQUESTED"]);

function normalizeStatus(value) {
  return String(value || "").trim().toUpperCase().replace(/[-\s]+/g, "_");
}

export function derivePublishingWorkflow(book = {}) {
  const canonical = book.publication_workflow && typeof book.publication_workflow === "object"
    ? book.publication_workflow
    : {};
  const canonicalRights = canonical.rights || {};
  const canonicalDemand = canonical.demand || {};
  const canonicalIngestion = canonical.ingestion || {};
  const canonicalEdition = canonical.edition || {};
  const canonicalVisual = canonical.visual || {};
  const canonicalAudio = canonical.audio || {};
  const canonicalQa = canonical.qa || {};
  const canonicalCost = canonical.cost || {};
  const canonicalPublication = canonical.publication || {};
  const canonicalRelease = canonical.release || {};
  const rightsTier = normalizeStatus(canonicalRights.tier);
  const verificationStatus = normalizeStatus(canonicalRights.verification_status);
  const qaStatus = normalizeStatus(canonicalQa.status);
  const actionStatus = normalizeStatus(canonicalDemand.action_status);
  const ingestionStatus = normalizeStatus(canonicalRelease.content_status || canonicalIngestion.status);
  const editionStatus = normalizeStatus(canonicalEdition.status);
  const visualStatus = normalizeStatus(canonicalVisual.status);
  const audioStatus = normalizeStatus(canonicalRelease.audio_release || canonicalAudio.status);
  const costUsed = Number(canonicalCost.used ?? 0);
  const costBudget = Number(canonicalCost.budget ?? 0);
  const blockers = [];

  if (rightsTier === "C") blockers.push("BLOCKED_RIGHTS: Tier C cannot publish anywhere.");
  if (rightsTier === "B") blockers.push("REGION_GATED_REVIEW: Tier B is not eligible for normal global publication.");
  if (!["A", "B", "C"].includes(rightsTier)) blockers.push("Rights approval is required.");
  if (rightsTier === "A" && verificationStatus !== "APPROVED") blockers.push("Rights verification must be approved.");
  if (canonicalRights.blocked_reason) blockers.push("Rights blocked reason must be cleared.");
  if (actionStatus !== "READY_FOR_GENERATION") blockers.push("BLOCKED_PRIORITY_GATE: Phase 3 action_status must be READY_FOR_GENERATION.");
  if (!ALLOWED_INGESTION_STATUSES.has(ingestionStatus)) blockers.push("BLOCKED_INGESTION: Phase 4 ingestion_status must be INGESTED or CLEANED.");
  if (!ALLOWED_GENERATION_STATUSES.has(editionStatus)) blockers.push("BLOCKED_EDITION_GATE: Phase 5 edition_generation_status must be ready, partial dry-run, or QA passed.");
  if (!ALLOWED_GENERATION_STATUSES.has(visualStatus)) blockers.push("BLOCKED_VISUAL_GATE: Phase 6 visual_status must be ready, partial dry-run, or QA passed.");
  if (!ALLOWED_AUDIO_STATUSES.has(audioStatus)) blockers.push("BLOCKED_AUDIO_GATE: Phase 7 audio_status must be ready, QA passed, or AUDIO_NOT_REQUIRED.");
  if (qaStatus !== "QA_PASSED" && canonicalPublication.state !== "PUBLISHED") blockers.push("QA pass is required.");
  if (costBudget > 0 && costUsed > costBudget) blockers.push("BLOCKED_COST: Cost budget is exceeded.");
  const isPublished = canonicalPublication.state === "PUBLISHED";
  // An editorial/workflow Published label never clears independent evidence gates.

  let state = "DISCOVERED";
  if (canonicalPublication.archived) state = "ARCHIVED";
  else if (canonicalPublication.quarantined || rightsTier === "C" || canonicalRights.blocked_reason) state = "QUARANTINED";
  else if (canonicalPublication.paused) state = "PAUSED";
  else if (isPublished) state = "PUBLISHED";
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
      "content status": ingestionStatus || "MISSING",
      "reader release": canonicalRelease.reader_release || (canonicalPublication.reader_exposed ? "LIVE" : "DRAFT"),
      "audio release": canonicalRelease.audio_release || (canonicalPublication.audio_exposed ? "LIVE" : "NOT_REQUESTED"),
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
  const workflowAvailable = book.admin_reporting?.workflow?.status === "RECORDED";
  const workflow = workflowAvailable ? derivePublishingWorkflow(book) : null;
  return (
    <div className="mt-4 rounded-lg border border-brand-soft bg-white/50 p-3" data-testid={`publishing-workflow-${book.slug}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-[0.62rem] uppercase tracking-[0.18em] text-charcoal-soft">Recorded workflow · not customer acceptance</div>
          <div className="font-serif-display text-lg text-burgundy">{workflow ? workflow.state.replace(/_/g, " ") : "Workflow evidence unavailable"}</div>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-[0.6rem] uppercase tracking-[0.16em] ${workflow?.publishReadiness === "READY" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
          {workflow ? workflow.publishReadiness : "UNAVAILABLE"}
        </span>
      </div>
      {!workflow && (
        <p className="mt-3 text-xs text-amber-800">
          Publication readiness cannot be assessed because workflow evidence is missing or invalid.
        </p>
      )}
      {workflow?.blockers.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-amber-800" aria-label="Recorded workflow blockers">
          {workflow.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
        </ul>
      )}
      <dl className="mt-3 space-y-2 text-xs">
        {[
          ["Editorial label", "editorial"],
          ["Recorded rights/workflow evidence", "workflow"],
          ["Public preview capability", "preview"],
          ["Protected-text authority", "protected_text"],
          ["Audio capability", "audio"],
          ["End-to-end acceptance", "acceptance"],
        ].map(([label, key]) => {
          const report = book.admin_reporting?.[key];
          return <div key={key}>
            <dt className="font-medium">{label}</dt>
            <dd>{report?.status || "UNVERIFIED"} · {report?.source || "No authoritative reporting value supplied"}</dd>
          </div>;
        })}
      </dl>
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
