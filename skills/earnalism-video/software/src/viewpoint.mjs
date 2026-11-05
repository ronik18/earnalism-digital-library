// Deterministic explanatory bridge, not a physical camera simulation.
export const ease = x => {const u=Math.max(0,Math.min(1,x));return u*u*(3-2*u);};
export function observerBridge(t,anchor,origin,target) {
 const p=ease((t-anchor)/1.65);
 return {p,x:origin.x+(target.x-origin.x)*p+(p>0&&p<1&&Math.abs(target.x-origin.x)<1?330*Math.sin(Math.PI*p):0),y:origin.y+(target.y-origin.y)*p-60*Math.sin(Math.PI*p),scale:.08+.92*p};
}
export const quarterState=phase=>Math.abs(phase-.25)<.012;
export function layout(portrait){
 return portrait?{cx:470,cy:335,radius:205,card:{x:110,y:755,w:720,h:490},disk:{x:470,y:980,r:125},diskLabelY:1190,labelSize:48}:
 {cx:480,cy:310,radius:205,card:{x:790,y:80,w:560,h:535},disk:{x:1070,y:310,r:130},diskLabelY:505,labelSize:34};
}
// Reveal each fraction when its existing spoken explanation begins.
export function quarterComparison(scene,t,phase){
 const active=scene.diagram==='phases'&&quarterState(phase);
 const anchor=phrase=>scene.anchors?.find(a=>a.phrase===phrase)?.time;
 const half=anchor('At first quarter'),cycle=anchor('First quarter means');
 if(active&&(!Number.isFinite(half)||!Number.isFinite(cycle)))throw Error('Quarter comparison requires actual narration anchors');
 return {active,halfOpacity:active?ease((t-half)/.5):0,cycleOpacity:active?ease((t-cycle)/.5):0};
}
export const showReviewMark=props=>props.reviewOverlay!==false;

export const observerLabelsOpacity=(t,anchor,bridging)=>bridging?ease((t-anchor-1.65)/.3):1;
export const nearFull=phase=>Math.abs(((phase%1)+1)%1-.5)<.012;
