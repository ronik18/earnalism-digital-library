import React from 'react';
import {Img,staticFile,useVideoConfig} from 'remotion';
import {watermarkAsset,watermarkLayout} from './branding.mjs';
type WatermarkProps={surface?:'video'|'cover';placement?:{left:number;top:number;size:number};occupiedRects?:{x:number;y:number;width:number;height:number}[]};
export const BrandWatermark=({surface='video',placement,occupiedRects=[]}:WatermarkProps={})=>{
 const {width,height}=useVideoConfig(),c=watermarkAsset.crop,q=watermarkLayout(width,height,{surface,placement,occupiedRects});
 return <div aria-label="Earnalism emblem" style={{position:'absolute',top:q.top,right:q.right,width:q.size,height:q.size,overflow:'hidden',opacity:q.opacity,pointerEvents:'none',zIndex:20}}>
  <Img src={staticFile(watermarkAsset.path)} style={{position:'absolute',width:watermarkAsset.sourceWidth*q.scale,height:watermarkAsset.sourceHeight*q.scale,maxWidth:'none',left:-c.x*q.scale,top:-c.y*q.scale}}/>
 </div>;
};
