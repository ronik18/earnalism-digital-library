"""Optional matched-frame diagnostics; never infers audience preference or approval."""
from pathlib import Path
import argparse,json,subprocess

def rgb_difference(left,right):
 if len(left)!=len(right) or not left:raise ValueError('Equal nonempty RGB frames required')
 return sum(abs(a-b) for a,b in zip(left,right))/len(left)

def compare_frames(left,right,width=160,height=90):
 if min(width,height)<1:raise ValueError('Positive frame dimensions required')
 def decode(path):
  return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf',f'fps=1,scale={width}:{height}','-f','rawvideo','-pix_fmt','rgb24','-'])
 a,b=decode(left),decode(right);size=width*height*3
 if not a or len(a)%size or len(b)%size or len(a)!=len(b):raise ValueError('Matched frame counts required; align different timelines explicitly')
 return {'method':'One decoded frame per second, scaled RGB mean absolute difference; includes encoder noise. Not a perceptual score or an audience result.','frames':[{'sample':i//size,'rgb_difference_0_255':round(rgb_difference(a[i:i+size],b[i:i+size]),5)} for i in range(0,len(a),size)],'audience_preference':'UNKNOWN','human_approval':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('earlier');p.add_argument('latest');p.add_argument('--portrait',action='store_true');a=p.parse_args();print(json.dumps(compare_frames(Path(a.earlier),Path(a.latest),90 if a.portrait else 160,160 if a.portrait else 90),indent=2))
