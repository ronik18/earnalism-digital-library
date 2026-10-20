import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";

const TARGETS = Object.freeze([
  ["6d240429-48f2-445c-92a4-336aaca79e98", "the-art-of-money-getting"],
  ["32a20edc-5097-4d64-98d0-fb3d29487a9d", "the-call-of-the-wild"],
  ["0b8c99b9-c5c1-4fe1-997a-0a69300f9ba1", "the-cop-and-the-anthem"],
  ["599f3ccb-4111-4fa7-8596-32d9ffc3dc0a", "dsires-baby"],
  ["4df036e8-4052-4c7d-93d4-31884473488c", "love-of-life"],
  ["d4cb4472-7e0a-4bad-ab89-05f7d7ace821", "the-time-machine"],
]);
const ERROR_CODES = { 404: "ACTIVE_SEGMENT_VERSION_MISSING", 409: "ACTIVATION_STATE_OUT_OF_SYNC" };
const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
const versionString = (value) => typeof value === "string" && value.trim().length > 0 && value.length <= 512 && !/[\u0000-\u001f\u007f]/.test(value);
const measuredStatus = (value) => Number.isInteger(value) && value >= 100 && value <= 599 ? value : null;

function project(data, slug) {
  if (!data || typeof data !== "object" || Array.isArray(data) ||
      !["book_slug", "segmentation_version", "version", "activation_generation"].every((key) => own(data, key)) ||
      data.book_slug !== slug || !versionString(data.segmentation_version) || !versionString(data.version) ||
      !Number.isSafeInteger(data.activation_generation) || data.activation_generation < 0) return null;
  return { book_slug: data.book_slug, segmentation_version: data.segmentation_version,
    version: data.version, activation_generation: data.activation_generation };
}

export default function SixTitleActivationInspection() {
  const started = useRef(false);
  const controller = useRef(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [state, setState] = useState("NOT_RUN");
  const [rows, setRows] = useState(() => TARGETS.map(([snapshot_uuid, requested_slug]) => ({
    snapshot_uuid, requested_slug, endpoint: `/api/admin/reading-pass/books/${requested_slug}/segments/active`,
    outcome: "NOT_RUN", http_status: null, started_at: null, completed_at: null,
  })));
  useEffect(() => () => controller.current?.abort(), []);

  const inspect = async () => {
    if (started.current) return;
    started.current = true;
    setHasStarted(true);
    setState("RUNNING");
    const abort = new AbortController();
    controller.current = abort;
    for (let index = 0; index < TARGETS.length; index += 1) {
      if (abort.signal.aborted) return;
      const slug = TARGETS[index][1];
      const started_at = new Date().toISOString();
      let status = null;
      let data;
      try {
        const response = await api.get(`/admin/reading-pass/books/${slug}/segments/active`, {
          skipAuthRedirect: true, signal: abort.signal,
        });
        status = measuredStatus(response.status);
        data = response.data;
      } catch (error) {
        status = measuredStatus(error.response?.status);
        data = error.response?.data;
      }
      if (abort.signal.aborted) return;
      let result;
      let stop = true;
      if (status === 200) {
        const pointer = project(data, slug);
        result = pointer ? { outcome: "OBSERVED", pointer } : { outcome: "INVALID_RESPONSE" };
        stop = !pointer;
      } else {
        const validError = data && typeof data === "object" && !Array.isArray(data) &&
          own(data, "detail") && data.detail && typeof data.detail === "object" &&
          !Array.isArray(data.detail) && own(data.detail, "code") &&
          own(ERROR_CODES, status) && data.detail.code === ERROR_CODES[status];
        result = { outcome: status === null ? "NETWORK_OR_UNMEASURED" : "HTTP_ERROR",
          error_code: validError ? data.detail.code : "UNKNOWN" };
        stop = !validError;
      }
      setRows((previous) => previous.map((row, i) => i === index
        ? { ...row, started_at, completed_at: new Date().toISOString(), http_status: status, ...result } : row));
      if (stop) { setState("STOPPED"); return; }
    }
    if (!abort.signal.aborted) setState("COMPLETE");
  };

  return (
    <section aria-label="Six-title activation inspection" className="mb-5 rounded border p-4">
      <h3>Activation metadata inspection</h3>
      <p>Reads six fixed titles once per mounted inspection. Snapshot UUIDs are catalogue associations, not IDs verified by these responses.</p>
      <p>Pointer metadata does not establish loaded content, rights or admission. Generation zero may be a default; 404 means no active pointer and 409 means a state mismatch.</p>
      <button type="button" className="btn-secondary" disabled={hasStarted} onClick={inspect}>Read six activation pointers</button>
      <p role="status">{state}</p>
      <pre data-testid="six-title-activation-receipt" className="whitespace-pre-wrap break-words">{JSON.stringify(rows, null, 2)}</pre>
    </section>
  );
}
