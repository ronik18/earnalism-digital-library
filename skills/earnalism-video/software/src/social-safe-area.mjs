// Conservative Earnalism review profile based on observed organic mobile UI.
// These are configurable design reservations, not official platform dimensions.
export const portraitReviewProfile = Object.freeze({
  id: 'earnalism-organic-portrait-review-v1', width: 1080, height: 1920,
  top: 270, bottom: 420, left: 72, right: 180,
});

export function safeContentRect(profile = portraitReviewProfile) {
  const {width, height, top, bottom, left, right} = profile;
  if (![width, height, top, bottom, left, right].every(Number.isFinite) ||
      width <= 0 || height <= 0 || Math.min(top, bottom, left, right) < 0 ||
      left + right >= width || top + bottom >= height) throw Error('Invalid UI review profile');
  return {x: left, y: top, width: width - left - right, height: height - top - bottom};
}

// Scale the observed review reservations with the destination composition.
// Different aspect ratios still require their own actual crop/interface review.
export function reviewProfileForFrame(width, height, profile = portraitReviewProfile) {
  safeContentRect(profile);
  if (![width, height].every(Number.isFinite) || width <= 0 || height <= 0)
    throw Error('Invalid composition dimensions');
  const sx = width / profile.width, sy = height / profile.height;
  return {...profile, width, height, top: profile.top * sy,
    bottom: profile.bottom * sy, left: profile.left * sx, right: profile.right * sx};
}

export function assertUiClear(name, rect, profile = portraitReviewProfile) {
  const safe = safeContentRect(profile), {x, y, width, height} = rect;
  if (![x, y, width, height].every(Number.isFinite) || width <= 0 || height <= 0 ||
      x < safe.x || y < safe.y || x + width > safe.x + safe.width || y + height > safe.y + safe.height)
    throw Error('Essential content meets reserved mobile UI: ' + name);
  return rect;
}

export function uiMasks(profile = portraitReviewProfile) {
  safeContentRect(profile);
  const {width, height, top, bottom, left, right} = profile;
  return [
    {name: 'Top navigation / account row', x: 0, y: 0, width, height: top},
    {name: 'Right action rail', x: width - right, y: 0, width: right, height},
    {name: 'Lower account / post copy / audio', x: 0, y: height - bottom, width, height: bottom},
    {name: 'Left crop reserve', x: 0, y: 0, width: left, height},
  ];
}
