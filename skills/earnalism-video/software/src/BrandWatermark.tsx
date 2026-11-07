import React from 'react';
import {Img,staticFile,useVideoConfig} from 'remotion';
import {watermarkAsset,watermarkLayout} from './branding.mjs';
type WatermarkProps={surface?:'video'|'cover';placement?:{left:number;top:number;width?:number;size?:number};occupiedRects?:{x:number;y:number;width:number;height:number}[];backing?:'standard'|'feathered'};
export const BrandWatermark=({surface='video',placement,occupiedRects=[],backing='standard'}:WatermarkProps={})=>{
 const {width,height}=useVideoConfig(),q=watermarkLayout(width,height,{surface,placement,occupiedRects});
 if(!['standard','feathered'].includes(backing))throw Error('Unknown watermark backing');
 return <div aria-label="Earnalism full production logo and lettering" style={{position:'absolute',top:q.top,right:q.right,width:q.width,height:q.height,background:backing==='standard'?q.background:undefined,borderRadius:4,opacity:q.opacity,pointerEvents:'none',zIndex:20}}>
  {backing==='feathered'&&<div style={{position:'absolute',inset:0,background:q.background,borderRadius:12,maskImage:'linear-gradient(to right,transparent,#000 5%,#000 95%,transparent),linear-gradient(to bottom,transparent,#000 12%,#000 88%,transparent)',maskComposite:'intersect'}}/>}
  <Img src={staticFile(watermarkAsset.path)} style={{position:'relative',display:'block',width:'100%',height:'100%',objectFit:'contain'}}/>
 </div>;
};
