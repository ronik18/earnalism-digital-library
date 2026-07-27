export function cardZoneBoxes({ width = 560, height = 410, coverRatio = 0.42 } = {}) {
  const padding = 24;
  const gap = 20;
  const coverWidth = Math.max(180, Math.round((width - padding * 2) * coverRatio));
  const textWidth = width - padding * 2 - gap - coverWidth;
  const titleHeight = Math.min(126, Math.max(62, Math.round(textWidth / 7.2)));
  const descriptionHeight = 66;
  const chipsHeight = 48;
  const ctaHeight = 44;
  const metaHeight = 36;
  const x = padding + textWidth + gap;
  return {
    card: { x: 0, y: 0, width, height },
    meta: { x: padding, y: padding, width: textWidth, height: metaHeight },
    title: { x: padding, y: padding + metaHeight + 10, width: textWidth, height: titleHeight },
    description: { x: padding, y: padding + metaHeight + titleHeight + 18, width: textWidth, height: descriptionHeight },
    chips: { x: padding, y: height - padding - ctaHeight - chipsHeight - 8, width: textWidth, height: chipsHeight },
    covers: { x, y: padding, width: coverWidth, height: height - padding * 2 },
    cta: { x: padding, y: height - padding - ctaHeight, width: textWidth, height: ctaHeight },
  };
}

export function boxesIntersect(left, right) {
  return left.x < right.x + right.width
    && left.x + left.width > right.x
    && left.y < right.y + right.height
    && left.y + left.height > right.y;
}

export function geometryAudit(options) {
  const zones = cardZoneBoxes(options);
  const textZones = ["meta", "title", "description", "chips", "cta"];
  const intersections = [];
  textZones.forEach((zone) => {
    if (boxesIntersect(zones[zone], zones.covers)) intersections.push(`${zone}:covers`);
  });
  textZones.forEach((zone, index) => {
    textZones.slice(index + 1).forEach((other) => {
      if (boxesIntersect(zones[zone], zones[other])) intersections.push(`${zone}:${other}`);
    });
  });
  const outside = Object.entries(zones).filter(([key, box]) => key !== "card" && (
    box.x < 0 || box.y < 0 || box.x + box.width > zones.card.width || box.y + box.height > zones.card.height
  ));
  return { zones, intersection_count: intersections.length, outside_count: outside.length, intersections, outside: outside.map(([key]) => key) };
}
