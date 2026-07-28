const SHELF_AREA_ALIASES = Object.freeze({
  bengali: "bengali",
  "bengali-life-and-legacy": "bengali",
  "bengali-classics": "bengali",
  gothic: "gothic",
  "gothic-and-the-uncanny": "gothic",
  "gothic-classics": "gothic",
  love: "love",
  "love-society-and-human-nature": "love",
  "love-society-human-nature": "love",
  adventure: "adventure",
  "adventure-nature-and-wonder": "adventure",
  "adventure-journeys": "adventure",
  short: "short",
  "short-masterpieces": "short",
});

export const SHELF_AREAS = Object.freeze(["bengali", "gothic", "love", "adventure", "short"]);

export function normalizeShelfArea(groupOrArea = "") {
  const value = typeof groupOrArea === "string"
    ? groupOrArea
    : groupOrArea?.layout_area || groupOrArea?.id || "";
  const normalized = String(value).trim().toLowerCase();
  if (SHELF_AREA_ALIASES[normalized]) return SHELF_AREA_ALIASES[normalized];
  if (normalized.startsWith("bengali")) return "bengali";
  if (normalized.startsWith("gothic")) return "gothic";
  if (normalized.startsWith("love")) return "love";
  if (normalized.startsWith("adventure")) return "adventure";
  if (normalized.startsWith("short")) return "short";
  return normalized;
}

function row(areas) {
  return `"${areas.join(" ")}"`;
}

function weightedRow(areas) {
  if (areas.length === 1) return row(Array(12).fill(areas[0]));
  if (areas.length === 2) {
    return row([...Array(6).fill(areas[0]), ...Array(6).fill(areas[1])]);
  }
  const weights = { love: 4, adventure: 5, short: 3 };
  const total = areas.reduce((sum, area) => sum + (weights[area] || 1), 0);
  const cells = [];
  let used = 0;
  areas.forEach((area, index) => {
    const remainingAreas = areas.length - index - 1;
    const remainingCells = 12 - used;
    const desired = index === areas.length - 1
      ? remainingCells
      : Math.max(1, Math.round((weights[area] || 1) / total * 12));
    const count = Math.min(desired, remainingCells - remainingAreas);
    cells.push(...Array(count).fill(area));
    used += count;
  });
  return row(cells);
}

function orderedAreas(areas) {
  return [
    ...SHELF_AREAS.filter((area) => areas.has(area)),
    ...Array.from(areas).filter((area) => !SHELF_AREAS.includes(area)),
  ];
}

function tabletRowsFor(areas) {
  const available = orderedAreas(areas);
  const rows = [];
  if (available.includes("bengali") && available.includes("gothic")) {
    rows.push(row(["bengali", "bengali"]));
    const lower = available.filter((area) => area !== "bengali");
    for (let index = 0; index < lower.length; index += 2) {
      const pair = lower.slice(index, index + 2);
      rows.push(row(pair.length === 1 ? [pair[0], pair[0]] : pair));
    }
    return rows;
  }
  for (let index = 0; index < available.length; index += 2) {
    const pair = available.slice(index, index + 2);
    rows.push(row(pair.length === 1 ? [pair[0], pair[0]] : pair));
  }
  return rows;
}

export function buildShelfGridLayout(groups = []) {
  const areas = new Set(groups.map(normalizeShelfArea).filter(Boolean));
  const rows = [];
  if (areas.has("bengali") && areas.has("gothic")) {
    rows.push(row([
      ...Array(7).fill("bengali"),
      ...Array(5).fill("gothic"),
    ]));
    const lower = SHELF_AREAS.filter((area) => areas.has(area) && !["bengali", "gothic"].includes(area));
    if (lower.length) rows.push(weightedRow(lower));
  } else {
    const available = orderedAreas(areas);
    for (let index = 0; index < available.length; index += 3) {
      rows.push(weightedRow(available.slice(index, index + 3)));
    }
  }

  return {
    areas,
    desktop: rows.join(" "),
    desktopRowCount: rows.length,
    tablet: tabletRowsFor(areas).join(" "),
    tabletRowCount: tabletRowsFor(areas).length,
    mobile: orderedAreas(areas).map((area) => row([area])).join(" "),
    mobileRowCount: areas.size,
  };
}
