"""Focused rendered-label presence regression, not OCR or graphical approval."""
import subprocess

def ink_pixels(rgb,reference=(155,180,195),tolerance=14):
 if len(rgb)%3:raise ValueError('Complete RGB pixels required')
 return sum(all(abs(pixel-reference[j])<=tolerance for j,pixel in enumerate(rgb[i:i+3])) for i in range(0,len(rgb),3))

def check(media,box,seconds=0,minimum=100,reference=(155,180,195),tolerance=14):
 x,y,w,h=map(int,box)
 if min(x,y)<0 or min(w,h,minimum)<1:raise ValueError('Valid pixel region and minimum required')
 raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(seconds),'-i',str(media),'-frames:v','1','-vf',f'format=rgb24,crop={w}:{h}:{x}:{y}','-f','rawvideo','-'])
 if len(raw)!=w*h*3:raise ValueError('Missing or incomplete rendered label region')
 count=ink_pixels(raw,reference,tolerance)
 if count<minimum:raise ValueError('Label ink missing or obscured in rendered region')
 return {'matching_ink_pixels':count,'minimum':minimum,'scope':'Presence of expected label-color pixels only; not text correctness, full readability or human graphical approval','human_approval':False}
