from pathlib import Path
import json,subprocess,numpy as np
O=Path(__file__).parent;R=Path('/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/internal/audiobook_lab/release_gate/sredni-vashtar_20260705T195720Z');master=R/'sredni-vashtar_openai_tts_final.mp3'
def pcm(p,start,seconds):
 raw=subprocess.check_output(['ffmpeg','-v','error','-nostdin','-ss',str(start),'-i',str(p),'-t',str(seconds),'-ac','1','-ar','8000','-f','f32le','-']);return np.frombuffer(raw,dtype='<f4').astype(np.float64)
def similarity(a,b):
 best=(-1,None)
 for lag in range(-256,257):
  aa=a[max(0,lag):min(len(a),len(b)+lag)];bb=b[max(0,-lag):min(len(b),len(a)-lag)]
  if len(aa)<1000:continue
  den=np.linalg.norm(aa)*np.linalg.norm(bb);v=float(np.dot(aa,bb)/den) if den else 0
  if v>best[0]:best=(v,lag)
 return {'max_normalized_correlation':best[0],'lag_seconds':best[1]/8000,'scope':'Decoded local waveform similarity only, not wording/listening approval'}
rows={'chunk_0_tail_vs_master':similarity(pcm(R/'tts_chunks/chunk_0000_585060d3c576.mp3',150,5.4),pcm(master,150,5.4)),'chunk_1_head_vs_master':similarity(pcm(R/'tts_chunks/chunk_0001_1a88e87d38f6.mp3',0,4),pcm(master,155.4,4))}
d={'boundary_seconds':155.4,'source':'Original local chunks compared with the retained master; no synthesis or external transfer','observations':rows,'interpretation':'High similarity on both sides supports that the master retained the original chunk speech at this join; it does not establish lexical completeness or justify an automatic splice.','new_allocation':False,'new_synthesis':False,'release_ready':False};(O/'boundary-acoustic-comparison.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(rows,indent=2))
