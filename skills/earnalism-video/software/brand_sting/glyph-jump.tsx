import React from 'react';
import {AbsoluteFill,Composition,registerRoot,useCurrentFrame,useVideoConfig,staticFile,Html5Audio,interpolate,Easing} from 'remotion';
const Film=({variant}:{variant:number})=>{const t=useCurrentFrame()/useVideoConfig().fps;
 const val=(times:number[],values:number[])=>interpolate(t,times,values,{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.inOut(Easing.sin)});
 let x=0,y=0,angle=0,ly=0,cy=0;
 if(variant===1)y=val([0,.16,.50,.80,1.03,1.16,1.30,1.45,3],[250,250,-125,-70,0,-28,0,0,0]);
 if(variant===2){ly=val([0,.12,.42,.65,.83,1,1.15,3],[230,230,-90,-40,0,-17,0,0]);cy=val([0,.42,.70,.96,1.12,1.27,1.42,3],[260,260,-115,-55,0,-20,0,0]);}
 if(variant===3){x=val([0,.12,.42,.76,1.02,1.19,1.36,3],[-200,-200,-115,-30,0,0,0,0]);y=val([0,.12,.42,.76,1.02,1.19,1.36,3],[200,200,-160,-85,0,-20,0,0]);angle=val([0,.12,.42,.76,1.02,1.36,3],[-12,-12,-9,4,-2,0,0]);}
 const visible=val([.1,.2],[0,1]);
 return <AbsoluteFill style={{background:'radial-gradient(ellipse at 50% 40%,#fffdf7,#efe1c5)'}}>{variant>0&&<Html5Audio src={staticFile(`brand-sting/jump-${variant}.wav`)}/>}<div style={{position:'absolute',inset:58,border:'1px solid #bd965c44'}}/>
 <svg width="1360" height="408" viewBox="0 0 2400 720" style={{position:'absolute',left:280,top:336,overflow:'visible'}}>
 <defs><mask id="rest"><rect width="2400" height="720" fill="white"/><rect x="707" y="40" width="181" height="350" fill="black"/></mask><clipPath id="glyph"><rect x="707" y="40" width="181" height="350"/></clipPath><clipPath id="ell"><rect x="707" y="40" width="181" height="250"/></clipPath><clipPath id="caret"><rect x="707" y="290" width="181" height="100"/></clipPath></defs>
 <image href={staticFile('brand-sting/production-lockup.png')} width="2400" height="720" mask={variant===0?undefined:'url(#rest)'}/>
 {variant===2?<>{[['ell',ly,.12],['caret',cy,.43]].map(([clip,dy,start])=><g key={clip as string} transform={`translate(0 ${dy})`} opacity={val([start as number,(start as number)+.1],[0,1])}><image href={staticFile('brand-sting/production-lockup.png')} width="2400" height="720" clipPath={`url(#${clip})`}/></g>)}</>:<g transform={`translate(${x} ${y}) rotate(${angle} 797 215)`} opacity={variant===0?0:visible}><image href={staticFile('brand-sting/production-lockup.png')} width="2400" height="720" clipPath="url(#glyph)"/></g>}
 </svg></AbsoluteFill>};
registerRoot(()=><>{[0,1,2,3].map(variant=><Composition key={variant} id={`Jump${variant}`} component={Film} defaultProps={{variant}} width={1920} height={1080} fps={60} durationInFrames={180}/>)}</>);
