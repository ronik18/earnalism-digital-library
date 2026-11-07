import {orbitLabel,landscapeSightlineY,earthLabelRegion} from './readability.mjs';
import React from 'react';
import {orbitalPosition,litFraction} from './lunar-geometry.mjs';
import {observerBridge,layout,quarterState,ease,quarterComparison,observerLabelsOpacity,nearFull} from './viewpoint.mjs';
const cyan='#8cd7df',gold='#e1b76d',white='#f5eedb',muted='#9bb4c3';
export const OrbitScene=({scene,t,phase,portrait,Moon}:any)=>{
 const q=layout(portrait),pos=orbitalPosition(phase,q.cx,q.cy,q.radius),card=q.card;
 const ground=scene.anchors?.find((a:any)=>a.phrase==='From the ground')?.time??scene.start;
 const bridge=observerBridge(t,ground,{x:q.cx,y:q.cy},q.disk),bridging=scene.diagram==='orbit';
 const p=bridging?bridge.p:1,comparison=quarterComparison(scene,t,phase),quarter=comparison.active;
 const txt=(x:number,y:number,s:string,size=q.labelSize,color=muted)=>{const item=orbitLabel(portrait,s,size);return <text x={x} y={y} textAnchor="middle" fill={color} fontSize={item.size}>{item.text}</text>;};
 const labelsOpacity=observerLabelsOpacity(t,ground,bridging);
 const beam=bridging?ease((t-ground+.6)/1.1):1;
 return <g>
  {txt(q.cx,portrait?65:55,'FROM ABOVE',portrait?44:29,white)}
  {[q.cy-65,q.cy,q.cy+65].map(y=><line key={y} x1={portrait?90:25} x2={portrait?185:120} y1={y} y2={y} stroke={gold} strokeWidth="4" markerEnd="url(#arrow)"/>)}
  {txt(portrait?135:125,q.cy-110,'Sunlight',portrait?42:30,gold)}
  <circle cx={q.cx} cy={q.cy} r={q.radius} fill="none" stroke="#38566a" strokeWidth="2" strokeDasharray="6 10"/>
  {quarter&&<path opacity={comparison.cycleOpacity} d={`M${q.cx-q.radius},${q.cy} A${q.radius},${q.radius} 0 0 1 ${q.cx},${q.cy-q.radius}`} fill="none" stroke={gold} strokeWidth="10"/>}
  <line x1={q.cx} y1={q.cy} x2={q.cx+(pos.x-q.cx)*beam} y2={q.cy+(pos.y-q.cy)*beam} stroke={cyan} strokeWidth="4" strokeDasharray="9 8"/>
  <circle cx={q.cx} cy={q.cy} r="43" fill="#438ca4" stroke={cyan} strokeWidth="3"/>
  <g transform={`translate(${pos.x},${pos.y})`}><circle r="32" fill={white}/><path d="M0,-32 A32,32 0 0,1 0,32 Z" fill="#263b4b"/><circle r="39" fill="none" stroke={cyan} strokeWidth="3"/></g>
  <path d={`M${q.cx+15},${q.cy-12} l17,12 -17,12 z`} fill={white} transform={`rotate(${Math.atan2(pos.y-q.cy,pos.x-q.cx)*180/Math.PI},${q.cx},${q.cy})`}/>
  {!quarter&&<g opacity={beam}>{txt(q.cx,portrait?640:landscapeSightlineY,'Cyan = our sightline',portrait?42:29,cyan)}</g>}
  {!bridging&&<path d={portrait?`M${pos.x},${pos.y} Q930,630 470,745`:`M${pos.x},${pos.y} Q730,145 780,330`} fill="none" stroke={cyan} strokeWidth="2" strokeDasharray="5 10" opacity=".5"/>}
  <g opacity={p}>
   <rect x={card.x} y={card.y} width={card.w} height={card.h} rx="28" fill="#102b39" stroke={cyan} strokeOpacity=".55"/>
   <g opacity={labelsOpacity}>{txt(q.disk.x,card.y+60,'FROM EARTH',portrait?48:34,cyan)}</g>
  </g>
  <g transform={bridging?`translate(${bridge.x},${bridge.y}) scale(${bridge.scale})`:`translate(${q.disk.x},${q.disk.y})`} opacity={bridging?Math.max(0,Math.min(1,(t-ground+.05)*3)):1}>
   <Moon phase={phase} r={q.disk.r} cx={0} cy={0}/>
  </g>
  <g opacity={quarter?0:labelsOpacity}>
   {txt(q.disk.x,q.diskLabelY,nearFull(phase)?'Almost fully lit':`${Math.round(100*litFraction(phase))}% of the disk lit`,portrait?48:36,white)}
  </g>
  {scene.diagram==='phases'&&!quarter&&txt(q.disk.x,portrait?720:50,quarter?'FIRST QUARTER':phase<.012?'NEW MOON':phase>.488?'FULL MOON':'Changing view',portrait?46:32,gold)}
  {quarter&&<g><g opacity={comparison.cycleOpacity}>{txt(q.cx,portrait?640:575,'¼ of the cycle',portrait?48:34,gold)}</g><g opacity={comparison.halfOpacity}>{txt(q.disk.x,portrait?q.diskLabelY:575,'½ of the visible disk',portrait?48:34,white)}</g><line opacity={Math.min(comparison.cycleOpacity,comparison.halfOpacity)} x1={portrait?q.cx:660} y1={portrait?680:565} x2={portrait?q.cx:770} y2={portrait?725:565} stroke={gold} strokeWidth="4" markerEnd="url(#arrow)"/></g>}

  <g data-role="earth-label-foreground"><rect {...earthLabelRegion(portrait,q.cx,q.cy)} fill="#071724"/>{txt(q.cx,q.cy+100,'Earth',portrait?44:32)}</g>
 </g>
};
