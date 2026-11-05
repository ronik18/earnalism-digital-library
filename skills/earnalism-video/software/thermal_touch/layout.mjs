// Thermal-touch composition bounds in delivery pixels, not browser-player coordinates.
export const sceneKinds = ['question', 'flow', 'material', 'temperature', 'reverse', 'callback'];
export const palette = {
  background: '#10251f', deep: '#091812', ivory: '#fff4de', muted: '#c4d4c7',
  amber: '#ffcb70', copper: '#c7865b', mint: '#a9d4b5', metal: '#94a6ad', wood: '#8c5439',
};
// Keep the visual end-ident onset on the same whole-frame boundary as the
// soundtrack finisher. Rounding down could begin the ident before speech ends.
export function bodyFrameCount(seconds, fps) {
  if (!Number.isFinite(seconds) || seconds <= 0 || !Number.isFinite(fps) || fps <= 0) throw Error('Finite positive body duration and frame rate required');
  const frames = Math.ceil(seconds * fps);
  if (!Number.isSafeInteger(frames) || frames < 1) throw Error('Body frame count is outside the supported range');
  return frames;
}
export function layoutFor(portrait) {
  return portrait ? {
    width: 1080, height: 1920,
    heading: {x: 70, y: 120, width: 870, height: 180},
    nativeCaptionCorridor: {x: 50, y: 310, width: 920, height: 195},
    diagram: {x: 70, y: 525, width: 870, height: 705},
    support: {x: 70, y: 1250, width: 870, height: 90},
    captions: {x: 70, y: 1400, width: 870, height: 180},
    essentialFont: 62, headingFont: 70, captionFont: 48,
  } : {
    width: 1920, height: 1080,
    heading: {x: 90, y: 58, width: 1620, height: 166},
    nativeCaptionCorridor: {x: 120, y: 840, width: 1680, height: 195},
    diagram: {x: 90, y: 225, width: 1740, height: 520},
    support: {x: 90, y: 770, width: 1740, height: 50},
    captions: {x: 180, y: 862, width: 1560, height: 150},
    essentialFont: 62, headingFont: 76, captionFont: 46,
  };
}
export const overlaps = (a, b) => a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
export function directionOfHeat(skinTemperature, objectTemperature) {
  if (!Number.isFinite(skinTemperature) || !Number.isFinite(objectTemperature)) throw Error('Finite temperatures required');
  return skinTemperature > objectTemperature ? 'hand-to-object' : skinTemperature < objectTemperature ? 'object-to-hand' : 'none';
}
export function sceneDirection(kind) {
  if (!sceneKinds.includes(kind)) throw Error('Unknown thermal scene ' + kind);
  return kind === 'reverse' ? directionOfHeat(30, 40) : directionOfHeat(33, 22);
}
export function flowGeometry(kind, center, handY, objectY) {
  const direction = sceneDirection(kind);
  return {direction, start: [center, direction === 'object-to-hand' ? objectY : handY], end: [center, direction === 'object-to-hand' ? handY : objectY]};
}
export function stateFor(kind, t, marks = {}) {
  if (!sceneKinds.includes(kind)) throw Error('Unknown thermal scene ' + kind);
  const contact = marks.contact ?? Infinity;
  const touched = kind === 'question' ? t >= contact : kind === 'flow' ? t >= (marks.touch ?? Infinity) : true;
  const afterNext = kind === 'callback' && t >= (marks.next ?? Infinity);
  const reversalWarm = kind === 'reverse' && t >= (marks.warm ?? Infinity);
  return {
    touched,
    afterNext,
    reversalWarm,
    showFlow: kind === 'reverse' ? t >= (marks.reverse ?? Infinity) : ['material', 'temperature'].includes(kind) || (['flow', 'question'].includes(kind) && touched),
    direction: sceneDirection(kind),
    // A room reading must never masquerade as a live contact-temperature reading.
    temperatureCaption: kind === 'reverse' && reversalWarm ? 'Warmer than skin' : touched ? 'Starting 22°C' : '22°C',
    numericTemperatureIsInitial: touched && kind !== 'reverse',
    context: kind === 'reverse' ? 'Illustration only · do not touch hot surfaces' : 'Illustrative room-temperature comparison',
  };
}
export function diagramMetrics(portrait) {
  const l = layoutFor(portrait), w = l.diagram.width;
  const metrics = portrait ? {
    width: w, height: 705, centers: [215, 655], blockY: 365, blockWidth: 330, blockHeight: 195,
    palmY: 150, fingerY: 195, fingerHeight: 170, chipY: 645, materialLabelY: 630,
  } : {
    width: w, height: 520, centers: [435, 1305], blockY: 270, blockWidth: 520, blockHeight: 150,
    palmY: 147, fingerY: 180, fingerHeight: 90, chipY: 480, materialLabelY: 492,
  };
  return {...metrics, handBounds: metrics.centers.map(cx => handGeometry(cx, metrics).bounds)};
}
export function handGeometry(center, metrics) {
  // Four fingers plus a separate non-contacting thumb form one natural hand.
  // Contact is qualitative: digit count never scales the energy arrows.
  const fingers = [
    {name: 'index', dx: -61, width: 40, root: 8},
    {name: 'middle', dx: -16, width: 44, root: 0},
    {name: 'ring', dx: 31, width: 40, root: 8},
    {name: 'little', dx: 72, width: 32, root: 24},
  ].map(f => ({name: f.name, x: center + f.dx - f.width / 2,
    y: metrics.fingerY + f.root, width: f.width,
    height: metrics.blockY - metrics.fingerY - f.root}));
  return {
    fingers,
    thumb: {name: 'thumb', x: center - 119, y: metrics.fingerY - 1, width: 43, height: 55, contactsSurface: false},
    wrist: {x: center - 34, y: metrics.palmY - 2, width: 68, height: metrics.fingerY - metrics.palmY + 10},
    bounds: {x: center - 122, y: metrics.palmY - 4, width: 244, height: metrics.blockY - metrics.palmY + 4},
  };
}
export function heatArrowOffsets(metal) {
  // Reserve side gutters outside the full palm/thumb/four-finger silhouette.
  return metal ? [-145, 145] : [145];
}
export function contactIconGeometry() {
  const scale = .64, surface = 23;
  return {scale, surface,
    block: {x: -92, y: surface, width: 184, height: 58},
    hand: {palmY: -118, fingerY: -76, fingerHeight: 76 + surface / scale, blockY: surface / scale},
  };
}
export function temperatureChipLayout(portrait, initial) {
  if (!initial) return {
    rect: {x: -180, y: -49, width: 360, height: 83},
    icon: {x: -161, y: -35, width: 32, height: 65},
    value: {x: -90, y: -30, width: 230, height: 52},
    valueX: 25, valueBaseline: 14, valueFont: 56,
  };
  return portrait ? {
    rect: {x: -180, y: -69, width: 360, height: 115},
    label: {x: -115, y: -51, width: 230, height: 40},
    value: {x: -130, y: -9, width: 260, height: 47},
    valueX: 0, valueBaseline: 35, valueFont: 56, labelBaseline: -21, labelFont: 38,
  } : {
    rect: {x: -180, y: -49, width: 360, height: 83},
    label: {x: -90, y: -47, width: 180, height: 33},
    value: {x: -115, y: -12, width: 230, height: 44},
    valueX: 0, valueBaseline: 30, valueFont: 56, labelBaseline: -24, labelFont: 32,
  };
}
export function materialHeaderBounds(portrait) {
  const m = diagramMetrics(portrait);
  return m.centers.map(x => ({x: x - 150, y: 5, width: 300, height: 75}));
}
export function propertyRects(portrait) {
  return portrait
    ? [0, 235, 470].map(y => ({x: 0, y, width: 870, height: 210}))
    : [0, 600, 1200].map(x => ({x, y: 5, width: 540, height: 500}));
}
export function assertLayout(portrait) {
  const l = layoutFor(portrait);
  for (const name of ['heading', 'diagram', 'support', 'captions', 'nativeCaptionCorridor']) {
    const r = l[name];
    if (r.x < 0 || r.y < 0 || r.x + r.width > l.width || r.y + r.height > l.height) throw Error(name + ' leaves composition');
  }
  for (const name of ['heading', 'diagram', 'support']) {
    if (overlaps(l[name], l.nativeCaptionCorridor) || overlaps(l[name], l.captions)) throw Error(name + ' enters caption area');
  }
  if (portrait && (l.width - l.diagram.x - l.diagram.width < 140 || l.width - l.heading.x - l.heading.width < 140)) throw Error('Portrait essential right margin');
  return l;
}

// Keep condition text inside each comparison card, including portrait's narrow panels.
export function conditionLabelLayout(portrait, warm) {
  const m = diagramMetrics(portrait);
  return {fontSize: portrait ? 50 : 54, lineHeight: portrait ? 55 : 0,
    lines: portrait ? (warm ? ['Warmer than', 'skin'] : ['Starting', 'condition']) : [warm ? 'Warmer than skin' : 'Starting condition'],
    firstBaseline: portrait ? m.chipY - 17 : m.chipY,
    region: {x: -m.blockWidth / 2 - 12, y: m.blockY + m.blockHeight + (portrait ? 16 : 4), width: m.blockWidth + 24, height: m.height - 10 - (m.blockY + m.blockHeight + (portrait ? 16 : 4))}};
}
