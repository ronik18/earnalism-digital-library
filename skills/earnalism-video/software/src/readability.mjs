// Essential diagram copy is shortened before enlarging it; captions are separate.
export function orbitLabel(portrait,text,requested=48){
 if(portrait)return {text,size:requested};
 const concise={'Cyan = our sightline':'Our sightline','¼ of the cycle':'¼ cycle','½ of the visible disk':'½ disk lit'};
 return {text:concise[text]??text.replace(/% of the disk lit$/,'% lit'),size:Math.max(64,requested)};
}
export const openingHeading='Why a crescent, if the Moon is round?';
export const landscapeSightlineY=640;
// Foreground label masks clear connectors, with room for the orbiting Moon.
export function earthLabelRegion(portrait,cx,cy){return portrait?{x:cx-70,y:cy+60,width:140,height:65}:{x:cx-90,y:cy+50,width:180,height:76};}

export function questionHeading(scene){return typeof scene.heading==='string'&&scene.heading.trim()?scene.heading.trim():openingHeading;}
