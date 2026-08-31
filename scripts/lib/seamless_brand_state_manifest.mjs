import fs from "node:fs";
import path from "node:path";

export const SUPPORTED_INTERACTIONS = new Set([
  "none",
  "open-mobile-menu",
  "open-library-filters",
  "select-book-chapters",
  "scroll-to-footer",
  "sanitize-account-fixture",
]);

function describe(value) {
  return value === undefined ? "undefined" : JSON.stringify(value);
}

function stateError(index, state, field, received, expected) {
  const id = state?.id ? ` (id ${JSON.stringify(state.id)})` : "";
  return new Error(`State index ${index}${id}: invalid ${field}; received ${describe(received)}; expected ${expected}.`);
}

export function loadStateManifest(manifestPath) {
  const resolved = path.resolve(manifestPath);
  let contents;
  try {
    contents = fs.readFileSync(resolved, "utf8");
  } catch (error) {
    throw new Error(`Unable to read state manifest ${resolved}: ${error.message}`);
  }
  try {
    return JSON.parse(contents);
  } catch (error) {
    throw new Error(`Unable to parse state manifest ${resolved}: ${error.message}`);
  }
}

export function validateStateManifest(manifest, routeInventory) {
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    throw new Error(`State manifest: invalid manifest; received ${describe(manifest)}; expected an object.`);
  }
  if (!Array.isArray(manifest.states)) {
    throw new Error(`State manifest: invalid states; received ${describe(manifest.states)}; expected an array.`);
  }
  if (!routeInventory || !Array.isArray(routeInventory.routes)) {
    throw new Error(`Route inventory: invalid routes; received ${describe(routeInventory?.routes)}; expected an array.`);
  }

  const routes = new Set(routeInventory.routes.map((route) => typeof route === "string" ? route : route?.path));
  const fixtures = new Set(manifest.supported_fixtures || []);
  const ids = new Set();

  manifest.states.forEach((state, index) => {
    if (!state || typeof state !== "object" || Array.isArray(state)) {
      throw stateError(index, state, "state", state, "an object");
    }
    if (typeof state.id !== "string" || state.id.trim() === "") {
      throw stateError(index, state, "id", state.id, "a non-empty unique string");
    }
    if (ids.has(state.id)) {
      throw stateError(index, state, "id", state.id, "a unique string");
    }
    ids.add(state.id);
    if (typeof state.route !== "string" || state.route.trim() === "") {
      throw stateError(index, state, "route", state.route, "a non-empty inventory route");
    }
    if (!routes.has(state.route)) {
      throw stateError(index, state, "route", state.route, "a route present in the route inventory");
    }
    if (!Number.isInteger(state.viewport?.width) || state.viewport.width <= 0) {
      throw stateError(index, state, "viewport.width", state.viewport?.width, "a positive integer");
    }
    if (!Number.isInteger(state.viewport?.height) || state.viewport.height <= 0) {
      throw stateError(index, state, "viewport.height", state.viewport?.height, "a positive integer");
    }
    if (!Number.isFinite(state.zoom) || state.zoom <= 0) {
      throw stateError(index, state, "zoom", state.zoom, "a positive finite number");
    }
    if (!fixtures.has(state.fixture)) {
      throw stateError(index, state, "fixture", state.fixture, "a manifest-supported fixture");
    }
    if (!SUPPORTED_INTERACTIONS.has(state.interaction)) {
      throw stateError(index, state, "interaction", state.interaction, "a supported interaction");
    }
    if (!state.capture || typeof state.capture !== "object" || !Object.values(state.capture).some(Boolean)) {
      throw stateError(index, state, "capture", state.capture, "at least one enabled capture type");
    }
  });

  return manifest;
}

export function listStateRecords(manifest) {
  if (!Array.isArray(manifest?.states)) {
    throw new Error("State manifest: invalid states; received undefined; expected an array.");
  }
  return [...manifest.states];
}

export function selectStateRecords(manifest, requestedIds) {
  const records = listStateRecords(manifest);
  if (requestedIds === undefined) return records;
  if (!Array.isArray(requestedIds)) {
    throw new Error(`State filter: invalid requested IDs; received ${describe(requestedIds)}; expected an array.`);
  }
  const requested = new Set();
  requestedIds.forEach((id, index) => {
    if (typeof id !== "string" || id.trim() === "") {
      throw new Error(`State filter index ${index}: invalid state ID; received ${describe(id)}; expected a non-empty manifest state ID.`);
    }
    if (requested.has(id)) {
      throw new Error(`State filter index ${index}: invalid state ID; received ${describe(id)}; expected no duplicate requested IDs.`);
    }
    requested.add(id);
  });
  const known = new Set(records.map((state) => state.id));
  for (const id of requested) {
    if (!known.has(id)) throw new Error(`State filter: invalid state ID; received ${describe(id)}; expected a state ID present in the manifest.`);
  }
  return records.filter((state) => requested.has(state.id));
}
