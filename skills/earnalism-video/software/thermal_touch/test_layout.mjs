import assert from 'node:assert/strict';
import {layoutFor, assertLayout, overlaps, sceneKinds, stateFor, directionOfHeat, flowGeometry, diagramMetrics, propertyRects, temperatureChipLayout, materialHeaderBounds, bodyFrameCount, handGeometry, heatArrowOffsets, contactIconGeometry, conditionLabelLayout} from './layout.mjs';

assert.equal(bodyFrameCount(10.01, 30), 301, 'partial body frames must ceil to the finisher audio-ident boundary');
assert.equal(bodyFrameCount(10, 30), 300, 'whole frames must not gain a frame');
assert.equal(bodyFrameCount(1 / 30, 30), 1);
assert.equal(bodyFrameCount(Number.MIN_VALUE, 30), 1, 'positive very short bodies cannot create a zero-frame sequence');
for (const [seconds, fps] of [[0, 30], [-1, 30], [NaN, 30], [Infinity, 30], ['10', 30], [true, 30], [10, 0], [10, -30], [10, NaN], [10, Infinity], [10, '30'], [Number.MAX_VALUE, 30]]) {
  assert.throws(() => bodyFrameCount(seconds, fps), 'invalid duration/frame rate must fail explicitly');
}

for (const portrait of [false, true]) {
  const l = assertLayout(portrait), m = diagramMetrics(portrait);
  assert.equal(m.width, l.diagram.width);
  assert.equal(m.height, l.diagram.height);
  assert.ok(l.essentialFont >= 56);
  assert.ok(!overlaps(l.diagram, l.captions));
  assert.ok(!overlaps(l.support, l.captions));
  for (const h of m.handBounds) {
    for (let lift = 0; lift <= 60; lift += 2) {
      const moved = {x: l.diagram.x + h.x, y: l.diagram.y + h.y - lift, width: h.width, height: h.height};
      assert.ok(!overlaps(moved, l.nativeCaptionCorridor), 'complete hand trajectory must clear upper caption corridor');
      assert.ok(!overlaps(moved, l.captions), 'complete hand trajectory must clear burned captions');
      const local = {x: h.x, y: h.y - lift, width: h.width, height: h.height};
      for (const label of materialHeaderBounds(portrait)) assert.ok(!overlaps(local, label), 'lifted wrist/palm must clear material name');
    }
  }
  for (const cx of m.centers) {
    assert.ok(cx - m.blockWidth / 2 >= 0);
    assert.ok(cx + m.blockWidth / 2 <= m.width);
    const hand = handGeometry(cx, m);
    assert.deepEqual(hand.fingers.map(f => f.name), ['index', 'middle', 'ring', 'little'], 'each hand needs four fingers and a distinct thumb');
    assert.equal(hand.thumb.name, 'thumb');
    assert.equal(hand.fingers.length + 1, 5);
    assert.equal(hand.thumb.contactsSurface, false, 'thumb must not falsely imply fifth contact');
    assert.ok(hand.thumb.y + hand.thumb.height < m.blockY);
    assert.ok(hand.wrist.width < 100, 'wrist tapers naturally into palm');
    for (const [i, finger] of hand.fingers.entries()) {
      assert.equal(finger.y + finger.height, m.blockY, 'all four fingertips share the actual contact plane');
      assert.ok(finger.height >= 66 && finger.width >= 32, 'each extended fingertip remains substantial at small size');
      assert.ok(finger.x >= cx - m.blockWidth / 2 && finger.x + finger.width <= cx + m.blockWidth / 2);
      assert.ok(finger.x >= hand.bounds.x && finger.x + finger.width <= hand.bounds.x + hand.bounds.width);
      for (const next of hand.fingers.slice(i + 1)) assert.ok(!overlaps(finger, next), 'visible separation must remain between all four fingers');
      for (const lift of [0, 1, 30, 60]) assert.equal(finger.y + finger.height - lift, m.blockY - lift, 'all fingertips arrive and leave together under shared motion');
    }
    for (const metal of [false, true]) for (const dx of heatArrowOffsets(metal)) for (const kind of ['flow', 'material', 'reverse']) {
      const arrow = flowGeometry(kind, cx + dx, m.blockY - 80, m.blockY + 48), allowance = 20;
      const bounds = {x: arrow.start[0] - allowance, y: Math.min(arrow.start[1], arrow.end[1]) - allowance, width: allowance * 2, height: Math.abs(arrow.end[1] - arrow.start[1]) + allowance * 2};
      assert.ok(bounds.x >= cx - m.blockWidth / 2 && bounds.x + bounds.width <= cx + m.blockWidth / 2, 'side arrows, heads and moving strokes fit their material block');
      for (let lift = 0; lift <= 60; lift += 2) assert.ok(!overlaps(bounds, {...hand.bounds, y: hand.bounds.y - lift}), 'entire arrow path must clear palm, distinct thumb and all four fingers throughout motion');
    }
  }
  assert.ok(m.blockY + m.blockHeight < m.chipY - 30);
  for (const initial of [false, true]) {
    const chip = temperatureChipLayout(portrait, initial), r = chip.rect;
    assert.ok(m.chipY + r.y > m.blockY + m.blockHeight, 'temperature chip must not collide with block');
    assert.ok(m.chipY + r.y + r.height <= m.height, 'entire chip must remain inside SVG viewBox');
    for (const content of [chip.icon, chip.label, chip.value].filter(Boolean)) {
      assert.ok(content.x >= r.x && content.y >= r.y && content.x + content.width <= r.x + r.width && content.y + content.height <= r.y + r.height, 'number/qualifier/icon must fit chip');
    }
    if (chip.icon) assert.ok(!overlaps(chip.icon, chip.value), 'thermometer icon cannot cover temperature number');
    if (chip.label) assert.ok(!overlaps(chip.label, chip.value), 'Starting qualifier and temperature must have separate lines');
  }
  const cards = propertyRects(portrait);
  for (const [i, r] of cards.entries()) {
    assert.ok(r.x >= 0 && r.y >= 0 && r.x + r.width <= m.width && r.y + r.height <= m.height);
    for (const q of cards.slice(i + 1)) assert.ok(!overlaps(r, q));
  }
  const icon = contactIconGeometry(), iconHand = handGeometry(0, icon.hand), contactCard = cards[2];
  assert.equal(iconHand.fingers.length, 4, 'the summary contact icon must also use four fingertips and a thumb');
  for (const finger of iconHand.fingers) assert.equal((finger.y + finger.height) * icon.scale, icon.surface);
  const iconCx = portrait ? 125 : contactCard.width / 2, iconCy = portrait ? 104 : 190;
  assert.ok(iconCx + iconHand.bounds.x * icon.scale >= 3 && iconCx + (iconHand.bounds.x + iconHand.bounds.width) * icon.scale <= contactCard.width - 3);
  assert.ok(iconCy + iconHand.bounds.y * icon.scale >= 3 && iconCy + (icon.block.y + icon.block.height) <= contactCard.height - 3, 'complete five-digit summary icon stays inside its card');
}
assert.equal(directionOfHeat(33, 22), 'hand-to-object');
assert.equal(directionOfHeat(22, 33), 'object-to-hand');
assert.equal(directionOfHeat(22, 22), 'none');
assert.throws(() => directionOfHeat(NaN, 22));
for (const kind of sceneKinds) for (const center of [120, 500, 900]) {
  const g = flowGeometry(kind, center, 270, 365);
  assert.equal(g.start[0], g.end[0]);
  assert.equal(Math.sign(g.end[1] - g.start[1]), kind === 'reverse' ? -1 : 1, 'all arrows reverse with temperature ordering');
}
assert.equal(stateFor('question', 0).temperatureCaption, '22°C');
assert.equal(stateFor('question', 4).temperatureCaption, '22°C', 'a question cannot invent a contact anchor');
assert.equal(stateFor('question', 4, {contact: 3.4}).temperatureCaption, 'Starting 22°C');
assert.equal(stateFor('flow', 1, {touch: 2}).showFlow, false);
assert.equal(stateFor('flow', 3, {touch: 2}).showFlow, true);
for (const kind of sceneKinds.filter(x => !['question', 'flow', 'reverse'].includes(x))) {
  assert.equal(stateFor(kind, 0).temperatureCaption, 'Starting 22°C');
  assert.equal(stateFor(kind, 0).numericTemperatureIsInitial, true);
}
assert.equal(stateFor('flow', 3, {touch: 2}).temperatureCaption, 'Starting 22°C');
assert.equal(stateFor('reverse', 0).showFlow, false, 'missing speech anchor cannot invent reversal timing');
assert.equal(stateFor('reverse', 1, {warm: 1, reverse: 3}).showFlow, false);
assert.equal(stateFor('reverse', 3, {warm: 1, reverse: 3}).showFlow, true);
assert.equal(stateFor('reverse', 1, {warm: 1}).temperatureCaption, 'Warmer than skin');
assert.match(stateFor('reverse', 0).context, /do not touch hot surfaces/);
assert.equal(stateFor('callback', 1, {next: 5}).afterNext, false);
assert.equal(stateFor('callback', 6, {next: 5}).afterNext, true);
assert.throws(() => stateFor('unknown', 0));
console.log('PASS: five-digit contact geometry, full hand/arrow clearance, frame-ceiled ident boundary, caption rails, starting-temperature labels, heat-arrow reversal and planned callback');

for (const portrait of [false, true]) for (const warm of [false, true]) {
  const label = conditionLabelLayout(portrait, warm), m = diagramMetrics(portrait);
  assert.equal(label.lines.join(' '), warm ? 'Warmer than skin' : 'Starting condition');
  assert.ok(label.firstBaseline - label.fontSize >= label.region.y, 'condition label must clear the material block');
  assert.ok(label.firstBaseline + (label.lines.length - 1) * label.lineHeight + label.fontSize * .22 <= label.region.y + label.region.height, 'full condition label must remain inside card');
  assert.ok(label.region.y + label.region.height < m.height - 5);
  assert.equal(label.lines.length, portrait ? 2 : 1);
}
console.log('PASS: staged condition-label reflow preserves complete wording and vertical card clearance');
