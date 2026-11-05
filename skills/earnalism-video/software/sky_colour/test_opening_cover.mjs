import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {openingComparisonLayout,openingRevealState,coverComparisonLayout,sourceRoutes,pointOnSourceRoute,labelBounds,panelLabelLayout,rectOverlap} from './layout.mjs';

const rect=c=>({x:c.x,y:c.y,width:c.w,height:c.h});
const marks={question:2.16,light:9.84}; // Actual current-opening anchors; no inferred speech timing.
assert.equal(openingRevealState(0,marks).source,0);
assert.equal(openingRevealState(2.15,marks).source,0);
assert.ok(openingRevealState(2.50,marks).source>0,'Common source progresses during the actual spoken question');
assert.equal(openingRevealState(9.83,marks).travel,0);
assert.ok(openingRevealState(10,marks).travel>0,'Travel cues wait for the actual light phrase');
assert.deepEqual(openingRevealState(100,{}),{source:0,travel:0},'Missing timing must not invent a cue');

for(const portrait of [false,true]){
 for(const [kind,l] of [['opening',openingComparisonLayout(portrait)],['cover',coverComparisonLayout(portrait)]]){
  const cards=[l.day,l.dusk];
  assert.equal(rectOverlap(rect(cards[0]),rect(cards[1])),false);
  for(const c of cards){
   assert.ok(c.x>=0&&c.y>=0&&c.x+c.w<=l.width&&c.y+c.h<=l.height,'Real card geometry fits composition');
   const label=panelLabelLayout(c,l.labelSize,kind==='cover',c===l.dusk),box=label.box;
   assert.ok(box.x>=c.x&&box.x+box.width<=c.x+c.w&&box.y>=c.y&&box.y+box.height<c.y+c.h*.5,'Actual label backplates fit high inside each card');
   const old=labelBounds({x:label.x,y:label.y,size:label.size,text:label.text});
   assert.ok(box.width>old.width+24,'The uppercase display label has materially more padding than the undersized scientific-label estimate');
  }
  sourceRoutes(l).forEach((route,i)=>{
   assert.deepEqual(route.end,{x:cards[i].x+cards[i].w/2,y:cards[i].y},'Both common-source paths visibly touch their panel, never empty space');
   assert.deepEqual(pointOnSourceRoute(route,0),route.start);
   assert.deepEqual(pointOnSourceRoute(route,1),route.end);
   for(let phase=0;phase<=1;phase+=.01){const p=pointOnSourceRoute(route,phase);assert.ok(Number.isFinite(p.x)&&Number.isFinite(p.y)&&p.x>=0&&p.x<=l.width&&p.y>=0&&p.y<=cards[i].y);}
  });
  if(kind==='cover'){
   const h=l.headline;
   assert.ok(cards.every(c=>!rectOverlap(h,rect(c))),'Cover headline clears imagery');
   assert.ok(h.y+h.height<l.source.y-l.source.r,'Cover headline clears common-source glyph');
   const small=portrait?360:320;
   assert.ok(l.labelSize*small/l.width>=15,'Essential cover labels stay at least15px in the scoped small-size check');
  }
 }
}
const portrait=coverComparisonLayout(true);
for(const item of [portrait.headline,...[portrait.day,portrait.dusk].map(rect)]){
 assert.ok(item.y>=420&&item.y+item.height<=1500,'Portrait key content also survives a central square crop');
}
const renderer=readFileSync(new URL('./index.tsx',import.meta.url),'utf8');
const panel=renderer.slice(renderer.indexOf('function ComparisonPanel('),renderer.indexOf('function SourceComparison('));
assert.ok(panel.includes('dusk&&'),'Only sunset appearance contains a warm solar disk; the sky patch is not a blue Sun');
assert.ok(panel.includes('Blue patch of sky away from the Sun'));
assert.ok(panel.includes('React.useId()'),'Each rendered panel receives its own SVG clip ID');
assert.ok(panel.includes('clipPathUnits="userSpaceOnUse"'));
const clipStart=panel.indexOf('<g clipPath={`url(#${clipId})`}>'),clipEnd=panel.indexOf('</g><rect x={x} y={y}');
assert.ok(clipStart>=0&&clipEnd>clipStart,'Rounded clip wraps all picture artwork before the outline');
assert.ok(panel.indexOf('fill="#ffb877"')>clipStart&&panel.indexOf('fill="#ffb877"')<clipEnd,'Oversized sunset glow is inside the clip');
assert.ok(panel.indexOf('fill="#102338"')>clipStart&&panel.indexOf('fill="#102338"')<clipEnd,'Foreground landscape is inside the clip');
assert.ok(panel.indexOf('<text x={label.x}')>clipEnd,'Generously padded labels remain separate from clipped artwork');
assert.ok(renderer.includes('Same white upstream source connected to the two observed appearances'));
assert.ok(renderer.includes('white source light, not a blue-to-red photon change'));
assert.ok(renderer.includes('Why two colours?'));
assert.ok(renderer.includes('coverComparisonLayout(portrait)'),'Dedicated cover composition, not a grabbed video frame');
console.log('PASS: actual-mark opening progression, white source, connected routes, rounded artwork clipping, padded display labels, distinct covers and scoped portrait crop');
