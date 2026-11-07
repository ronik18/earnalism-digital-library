import React from 'react';
import {AbsoluteFill, Composition, Sequence, OffthreadVideo, registerRoot, useCurrentFrame, useVideoConfig, staticFile} from 'remotion';
import {BrandWatermark} from '../src/BrandWatermark';
import {assertLayout, bodyFrameCount, conditionLabelLayout, contactIconGeometry, diagramMetrics, flowGeometry, handGeometry, heatArrowOffsets, palette as P, propertyRects, stateFor, temperatureChipLayout} from './layout.mjs';

type Scene = {scene: string; start: number; end: number; marks?: Record<string, number>; text?: string};
type Props = {duration: number; visualBodySeconds?: number; scenes: Scene[]; captions?: {start: number; end: number; text: string}[]; outro?: boolean; burnCaptions?: boolean};
const ease = (t: number, a: number, b: number) => {const x = Math.max(0, Math.min(1, (t - a) / (b - a))); return x * x * (3 - 2 * x);};
const titles: Record<string, string> = {
  question: 'Same temperature.\nWhy feel colder?',
  flow: 'Follow the heat leaving your hand.',
  material: 'How quickly can it take up heat?',
  temperature: 'What sets those first moments?',
  reverse: 'Reverse the temperature order.',
  callback: 'Same start. Different heat transfer.',
};
function Thermometer({x, y, text, portrait, initial, active = false}: any) {
  const chip = temperatureChipLayout(portrait, initial), r = chip.rect;
  return <g transform={`translate(${x} ${y})`}>
    <rect x={r.x} y={r.y} width={r.width} height={r.height} rx="22" fill="#17382c" stroke={active ? P.amber : '#688b76'} strokeWidth={active ? 5 : 2}/>
    {!initial && <><path d="M-145 -29V5" stroke={P.ivory} strokeWidth="11" strokeLinecap="round"/><circle cx="-145" cy="15" r="15" fill={P.amber}/></>}
    {initial && <text x="0" y={chip.labelBaseline} textAnchor="middle" fill={P.muted} fontSize={chip.labelFont} fontWeight="600">Starting</text>}
    <text x={chip.valueX} y={chip.valueBaseline} textAnchor="middle" fill={P.ivory} fontSize={chip.valueFont} fontWeight="700">{text}</text>
  </g>;
}
function Hand({cx, m, lift = 0, reverse = false, cooling = 0}: any) {
  const pY = m.palmY, fY = m.fingerY, hand = handGeometry(cx, m), wrist = hand.wrist;
  return <g transform={`translate(0 ${-lift})`} aria-label={reverse ? 'Five-digit human hand: four fingertips touching, distinct thumb and wrist; hand cooler than illustrated warm objects' : 'Five-digit human hand: four fingertips touching, distinct thumb and wrist; hand warmer than room-temperature objects'}>
    {hand.fingers.map((finger: any) => <rect key={finger.name} x={finger.x} y={finger.y} width={finger.width} height={finger.height} rx={finger.width / 2} fill="url(#skin)" stroke="#a66a49" strokeWidth="1.8"/>)}
    <path d={`M${cx - 34} ${pY - 2}L${cx - 36} ${pY + 19}C${cx - 48} ${pY + 29} ${cx - 72} ${fY - 5} ${cx - 79} ${fY + 13}L${cx - 80} ${fY + 27}Q${cx - 70} ${fY + 39} ${cx - 56} ${fY + 30}Q${cx - 18} ${fY + 23} ${cx + 22} ${fY + 30}Q${cx + 61} ${fY + 46} ${cx + 87} ${fY + 31}L${cx + 85} ${fY + 19}C${cx + 77} ${fY - 3} ${cx + 48} ${pY + 29} ${cx + 36} ${pY + 19}L${cx + 34} ${pY - 2}Z`} fill="url(#skin)" stroke="#b67a54" strokeWidth="1.8"/>
    <path d={`M${cx - 73} ${fY - 1}C${cx - 92} ${fY - 5} ${cx - 108} ${fY + 6} ${cx - 117} ${fY + 24}Q${cx - 126} ${fY + 43} ${cx - 112} ${fY + 51}Q${cx - 99} ${fY + 57} ${cx - 89} ${fY + 40}L${cx - 70} ${fY + 20}Z`} fill="url(#skin)" stroke="#b67a54" strokeWidth="1.8"/>
    <ellipse cx={cx - 108} cy={fY + 36} rx="8" ry="11" transform={`rotate(28 ${cx - 108} ${fY + 36})`} fill="#f4d3b2" stroke="#d49b75" strokeWidth="1.5"/>
    <path d={`M${cx - 29} ${pY + 13}Q${cx} ${pY + 18} ${cx + 29} ${pY + 13}M${cx - 60} ${fY + 12}Q${cx - 42} ${fY + 2} ${cx - 28} ${fY + 10}`} stroke="#b67a54" strokeWidth="2" fill="none" opacity=".45"/>
    {hand.fingers.map((finger: any) => {
      const center = finger.x + finger.width / 2, tip = finger.y + finger.height, tintHeight = Math.min(80, finger.height * .8);
      return <g key={finger.name}>
        {cooling > 0 && <rect x={finger.x} y={tip - tintHeight} width={finger.width} height={tintHeight} rx={finger.width / 2} fill={P.mint} opacity={.18 * cooling}/>}
        <rect x={center - finger.width * .29} y={tip - 29} width={finger.width * .58} height="18" rx="7" fill="#f4d3b2" stroke="#d49b75" strokeWidth="2"/>
        <path d={`M${center - finger.width * .3} ${finger.y + finger.height * .52}Q${center} ${finger.y + finger.height * .52 - 5} ${center + finger.width * .3} ${finger.y + finger.height * .52}`} fill="none" stroke="#b87955" strokeWidth="2.5" opacity=".7"/>
      </g>;
    })}
  </g>;
}
function HeatArrow({kind, x, m, t, metal, index}: any) {
  const arrow = flowGeometry(kind, x, m.blockY - 80, m.blockY + 48), a = arrow.start, b = arrow.end;
  const phase = (t * (metal ? 1.1 : .42) + index * .29) % 1;
  const y = a[1] + (b[1] - a[1]) * phase;
  return <g aria-label={arrow.direction === 'hand-to-object' ? 'Energy transfer from hand to object' : 'Energy transfer from object to hand'}>
    <path d={`M${a[0]} ${a[1]}L${b[0]} ${b[1]}`} stroke={P.amber} strokeWidth={metal ? 9 : 5} opacity={metal ? .85 : .65} markerEnd="url(#heat-arrow)"/>
    <path d={`M${x} ${y - 10}V${y + 10}`} stroke={P.ivory} strokeWidth={metal ? 11 : 7} strokeLinecap="round"/>
  </g>;
}
function Comparison({kind, t, marks = {}, portrait, cover = false}: any) {
  const normalMetrics = diagramMetrics(portrait);
  const m = cover ? {...normalMetrics, blockY: 150, blockHeight: portrait ? 240 : 180, chipY: portrait ? 500 : 450} : normalMetrics;
  const s = stateFor(kind, t, marks);
  const contact = marks.contact ?? Infinity, touch = marks.touch ?? Infinity;
  const lift = cover ? 75 : kind === 'question' ? (Number.isFinite(contact) ? 60 * (1 - ease(t, contact - .8, contact)) : 60) : kind === 'flow' ? (Number.isFinite(touch) ? 60 * (1 - ease(t, touch - .8, touch)) : 60) : kind === 'callback' ? 55 * ease(t, marks.callback ?? 0, (marks.callback ?? 0) + 1.4) : 0;
  const revealFlow = kind === 'question' ? (Number.isFinite(contact) ? ease(t, contact, contact + .8) : 0) : kind === 'flow' ? (Number.isFinite(touch) ? ease(t, touch, touch + .7) : 0) : 1;
  const showStart = !['material', 'reverse'].includes(kind);
  return <svg viewBox={`0 0 ${m.width} ${m.height}`} width="100%" height="100%" aria-label="Illustrative comparison of a hand touching metal and wood; arrows show heat-transfer direction">
    <defs>
      <linearGradient id="steel" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#d6e0df"/><stop offset=".34" stopColor="#829b9c"/><stop offset=".5" stopColor="#c2cdca"/><stop offset="1" stopColor="#536c70"/></linearGradient>
      <linearGradient id="timber" x1="0" y1="0" x2="1" y2=".7"><stop stopColor="#b47a4f"/><stop offset=".5" stopColor="#8a5135"/><stop offset="1" stopColor="#5a3526"/></linearGradient>
      <linearGradient id="skin" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#f2c393"/><stop offset=".6" stopColor="#d39565"/><stop offset="1" stopColor="#a76448"/></linearGradient>
      <radialGradient id="local-warmth"><stop stopColor="#ffcb70" stopOpacity=".9"/><stop offset="1" stopColor="#ffcb70" stopOpacity="0"/></radialGradient>
      <marker id="heat-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0 0L10 5L0 10Z" fill={P.amber}/></marker>
      {m.centers.map((cx: number, i: number) => <clipPath id={'block-clip-' + i} key={i}><rect x={cx - m.blockWidth / 2} y={m.blockY} width={m.blockWidth} height={m.blockHeight} rx="15"/></clipPath>)}
    </defs>
    {m.centers.map((cx: number, i: number) => {
      const metal = i === 0, material = metal ? 'METAL' : 'WOOD';
      const materialMark = metal ? marks.metal : marks.wood;
      const materialShown = kind !== 'material' || (Number.isFinite(materialMark) && t >= materialMark);
      const flows = s.showFlow && !cover && materialShown;
      const warm = kind === 'material' && Number.isFinite(materialMark) ? ease(t, materialMark, materialMark + 2.8) : 0;
      const cooling = kind === 'material' && Number.isFinite(marks.cooling) ? ease(t, marks.cooling, marks.cooling + 1.1) * (metal ? 1 : .25) : 0;
      return <g key={material}>
        <rect x={cx - m.blockWidth / 2 - 25} y="5" width={m.blockWidth + 50} height={m.height - 10} rx="32" fill={metal ? '#294238' : '#332c21'} fillOpacity=".35" stroke={metal ? '#789a89' : '#a58d68'} strokeOpacity=".3" strokeWidth="2"/>
        <text x={cx} y="62" textAnchor="middle" fill={P.ivory} fontSize="62" fontWeight="750" letterSpacing="2">{material}</text>
        <rect x={cx - m.blockWidth / 2} y={m.blockY + 12} width={m.blockWidth} height={m.blockHeight} rx="15" fill="#020d09" opacity=".45"/>
        <rect x={cx - m.blockWidth / 2} y={m.blockY} width={m.blockWidth} height={m.blockHeight} rx="15" fill={metal ? 'url(#steel)' : 'url(#timber)'} stroke={metal ? '#d3e0da' : '#d5a16c'} strokeWidth="3"/>
        {!metal && <g clipPath={`url(#block-clip-${i})`} opacity=".35">{[20, 46, 83, 112, 151, 180].map((y, j) => <path key={y} d={`M${cx - m.blockWidth / 2 - 5} ${m.blockY + y}Q${cx - 40} ${m.blockY + y - 15 - j * 3} ${cx + m.blockWidth / 2 + 5} ${m.blockY + y + 7}`} stroke="#e0aa76" strokeWidth="3" fill="none"/>)}</g>}
        {s.reversalWarm && <rect x={cx - m.blockWidth / 2} y={m.blockY} width={m.blockWidth} height={m.blockHeight} rx="15" fill="#ffb45e" opacity=".25"/>}
        {warm > 0 && <g clipPath={`url(#block-clip-${i})`}>{handGeometry(cx, m).fingers.map((finger: any) => <ellipse key={finger.name} cx={finger.x + finger.width / 2} cy={m.blockY + 10} rx={(metal ? 95 : 40) * warm} ry={(metal ? 150 : 46) * warm} fill="url(#local-warmth)" opacity={metal ? .28 : .75}/>)}</g>}
        {!cover && <Hand cx={cx} m={m} lift={lift} reverse={kind === 'reverse'} cooling={cooling}/>}
        {flows && <g opacity={revealFlow}>{heatArrowOffsets(metal).map((dx, j) => <HeatArrow key={dx} kind={kind} x={cx + dx} m={m} t={t} metal={metal} index={j}/>)}</g>}
        {showStart && <Thermometer x={cx} y={m.chipY} text="22°C" portrait={portrait} initial={s.touched} active={kind === 'question' && Number.isFinite(marks.equal) && t >= marks.equal}/>}
        {kind === 'material' && materialShown && <text x={cx} y={m.materialLabelY} fill={P.ivory} fontSize={portrait ? 50 : 54} textAnchor="middle">{t >= (marks.cooling ?? Infinity) ? (metal ? 'Skin cools faster' : 'Less heat loss') : metal ? 'Spreads farther' : 'More localized'}</text>}
        {kind === 'reverse' && (() => {const label = conditionLabelLayout(portrait, s.reversalWarm); return <text x={cx} y={label.firstBaseline} fill={s.reversalWarm ? P.amber : P.muted} fontSize={label.fontSize} textAnchor="middle">{label.lines.map((line: string, j: number) => <tspan key={line} x={cx} dy={j === 0 ? 0 : label.lineHeight}>{line}</tspan>)}</text>;})()}
      </g>;
    })}
  </svg>;
}
function ColdGlass({portrait}: any) {
  const m = diagramMetrics(portrait), cx = m.width / 2, top = portrait ? 65 : 35, h = portrait ? 520 : 390;
  return <svg viewBox={`0 0 ${m.width} ${m.height}`} width="100%" height="100%" aria-label="Planned next lesson: droplets on the outside of a cold glass">
    <defs><linearGradient id="glass-fill" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#d8eee2" stopOpacity=".22"/><stop offset="1" stopColor="#7ebfb2" stopOpacity=".36"/></linearGradient></defs>
    <ellipse cx={cx} cy={top + h + 28} rx={h * .51} ry="25" fill="#030c07" opacity=".35"/>
    <path d={`M${cx - h * .33} ${top}L${cx - h * .26} ${top + h}Q${cx} ${top + h + 28} ${cx + h * .26} ${top + h}L${cx + h * .33} ${top}Z`} fill="url(#glass-fill)" stroke={P.mint} strokeWidth="5"/>
    <ellipse cx={cx} cy={top} rx={h * .33} ry="22" stroke={P.mint} strokeWidth="5" fill="#1d4034"/>
    {[[-.28, .28], [.3, .4], [-.26, .68], [.27, .76]].map(([x, y], i) => <path key={i} transform={`translate(${cx + x * h} ${top + y * h})`} d="M0 -18Q-20 7 -13 18Q0 34 13 18Q20 7 0 -18Z" fill="#b4e4d6" stroke="#e3fff1" strokeWidth="2"/>)}
    <text x={cx} y={m.height - 20} textAnchor="middle" fill={P.ivory} fontSize={portrait ? 52 : 58}>Where did the water come from?</text>
  </svg>;
}
function Properties({portrait, t, marks}: any) {
  const m = diagramMetrics(portrait), cards = propertyRects(portrait), contact = contactIconGeometry();
  return <svg viewBox={`0 0 ${m.width} ${m.height}`} width="100%" height="100%" aria-label="Summary of thermal response: energy conduction, energy storage and contact">
    <defs><linearGradient id="conducts" x1="0" x2="1"><stop stopColor={P.amber}/><stop offset="1" stopColor="#637f70"/></linearGradient><linearGradient id="skin" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#f2c393"/><stop offset=".6" stopColor="#d39565"/><stop offset="1" stopColor="#a76448"/></linearGradient><marker id="property-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0 0L10 5L0 10Z" fill={P.ivory}/></marker></defs>
    {cards.map((r: any, i: number) => {
      const active = i === 1 && Number.isFinite(marks.stores) && t >= marks.stores;
      const cx = portrait ? 125 : r.width / 2, cy = portrait ? 104 : 190;
      return <g key={i} transform={`translate(${r.x} ${r.y})`}>
        <rect x="3" y="3" width={r.width - 6} height={r.height - 6} rx="28" fill={active ? '#384b2f' : '#18382b'} stroke={active ? P.amber : '#6c8c75'} strokeWidth={active ? 4 : 2}/>
        <g transform={`translate(${cx} ${cy})`}>
          {i === 0 ? <><rect x="-88" y="-48" width="176" height="96" rx="14" fill="url(#conducts)"/><path d="M-62 0H60" stroke={P.ivory} strokeWidth="7" markerEnd="url(#property-arrow)"/></> : i === 1 ? <><rect x="-80" y="-68" width="160" height="136" rx="15" fill="#a87949" stroke={P.amber} strokeWidth="3"/>{[-36, 0, 36].map(y => <path key={y} d={`M-48 ${y}H48`} stroke={P.amber} strokeWidth="12" strokeLinecap="round"/>)}</> : <><rect x={contact.block.x} y={contact.block.y} width={contact.block.width} height={contact.block.height} rx="10" fill="#94aaa0"/><g transform={`scale(${contact.scale})`}><Hand cx={0} m={contact.hand}/></g><path d="M-74 26H74" stroke={P.amber} strokeWidth="5"/></>}
        </g>
        <text x={portrait ? 270 : r.width / 2} y={portrait ? 124 : 402} textAnchor={portrait ? 'start' : 'middle'} fill={P.ivory} fontSize={portrait ? 62 : 64} fontWeight="700">{['Conducts', 'Stores energy', 'Contact'][i]}</text>
      </g>;
    })}
  </svg>;
}
function supportFor(kind: string, t: number, marks: any) {
  if (kind === 'question') return t < (marks.contact ?? Infinity) ? 'Example: both start at 22°C.' : 'Your hand loses heat faster to metal.';
  if (kind === 'flow') return 'Marks show energy transfer.';
  if (kind === 'material') return 'Schematic energy spread';
  if (kind === 'temperature') return t >= (marks.touch ?? Infinity) ? 'Touch is not a thermometer.' : t >= (marks.stores ?? Infinity) ? 'Thickness and surface matter too.' : 'More than conductivity alone.';
  if (kind === 'reverse') return 'Animation only · do not touch hot surfaces.';
  return t < (marks.next ?? Infinity) ? 'A feeling depends on heat transfer.' : 'Next lesson · planned';
}
function Body(p: Props) {
  const {width, height, fps} = useVideoConfig(), portrait = height > width, l = assertLayout(portrait), time = useCurrentFrame() / fps;
  const scene = p.scenes.find(s => time >= s.start && time < s.end) || p.scenes.at(-1);
  if (!scene) return <AbsoluteFill style={{background: P.background}}><BrandWatermark/></AbsoluteFill>;
  const kind = scene.scene, t = Math.max(0, time - scene.start), marks = scene.marks || {}, s = stateFor(kind, t, marks), cue = p.captions?.find(c => time >= c.start && time < c.end);
  const header = kind === 'callback' && s.afterNext ? 'Another everyday question…' : titles[kind];
  const rect = (r: any): React.CSSProperties => ({position: 'absolute', left: r.x, top: r.y, width: r.width, height: r.height});
  return <AbsoluteFill style={{background: 'radial-gradient(ellipse at 28% 30%, #2b4938 0%, #10251f 57%, #091812 100%)', color: P.ivory, fontFamily: 'Arial,sans-serif'}}>
    <div style={{...rect(l.heading), fontSize: l.headingFont, fontWeight: 750, lineHeight: 1.09, whiteSpace: 'pre-line'}}>{header}</div>
    <div style={rect(l.diagram)}>{s.afterNext ? <ColdGlass portrait={portrait}/> : kind === 'temperature' ? <Properties portrait={portrait} t={t} marks={marks}/> : <Comparison kind={kind} t={t} marks={marks} portrait={portrait}/>}</div>
    <div style={{...rect(l.support), display: 'flex', alignItems: 'center', color: kind === 'reverse' ? P.amber : P.muted, fontSize: portrait ? 41 : 42, lineHeight: 1.15}}>{supportFor(kind, t, marks)}</div>
    {cue && p.burnCaptions && <div style={{...rect(l.captions), display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '14px 18px', borderRadius: 12, background: 'rgba(3,12,8,.91)', textAlign: 'center', fontSize: l.captionFont, lineHeight: 1.2}}>{cue.text}</div>}
    <BrandWatermark/>
  </AbsoluteFill>;
}
function Film(p: Props) {
  const {fps, height, width} = useVideoConfig(), bodyFrames = bodyFrameCount(p.visualBodySeconds ?? p.duration, fps);
  return <AbsoluteFill><Sequence durationInFrames={bodyFrames}><Body {...p}/></Sequence>{p.outro && <Sequence from={bodyFrames} durationInFrames={90}><OffthreadVideo muted src={staticFile(height > width ? 'outro-portrait.mp4' : 'outro-landscape.mp4')} style={{width, height}}/></Sequence>}</AbsoluteFill>;
}
const CleanFilm = (p: Props) => <Film {...p} burnCaptions={false}/>;
const CaptionedFilm = (p: Props) => <Film {...p} burnCaptions={true}/>;
function Cover() {
  const {height, width} = useVideoConfig(), portrait = height > width;
  return <AbsoluteFill style={{background: 'radial-gradient(ellipse at 40% 42%, #40573b, #10251f 70%)', color: P.ivory, fontFamily: 'Arial,sans-serif'}}>
    <div style={{position: 'absolute', left: portrait ? 85 : 100, top: portrait ? 450 : 95, width: portrait ? 910 : 1640, fontSize: portrait ? 104 : 116, lineHeight: 1.03, fontWeight: 800}}>SAME<br/><span style={{color: P.amber}}>TEMPERATURE?</span></div>
    <div style={{position: 'absolute', left: portrait ? 60 : 90, top: portrait ? 760 : 380, width: portrait ? 900 : 1740, height: portrait ? 780 : 600}}><Comparison kind="question" t={0} portrait={portrait} cover/></div>
    <BrandWatermark surface="cover"/>
  </AbsoluteFill>;
}
const defaults: Props = {duration: 90, scenes: [], captions: [], burnCaptions: false, outro: true};
registerRoot(() => <>
  {(['Landscape', 'Shorts', 'CleanShorts'] as const).map(f => <Composition key={f} id={'Thermal' + f} component={f === 'CleanShorts' ? CleanFilm : f === 'Shorts' ? CaptionedFilm : Film} width={f === 'Landscape' ? 1920 : 1080} height={f === 'Landscape' ? 1080 : 1920} fps={30} durationInFrames={2790} defaultProps={{...defaults, burnCaptions: f === 'Shorts'}} calculateMetadata={({props}) => ({durationInFrames: bodyFrameCount(props.visualBodySeconds ?? props.duration, 30) + (props.outro ? 90 : 0)})}/>)}
  {(['Landscape', 'Shorts'] as const).map(f => <Composition key={'Cover' + f} id={'Cover' + f} component={Cover} width={f === 'Landscape' ? 1920 : 1080} height={f === 'Landscape' ? 1080 : 1920} fps={30} durationInFrames={1}/>)}
</>);
