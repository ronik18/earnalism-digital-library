"""Frame-bound silent video replacement; retain final soundtrack separately."""
from pathlib import Path
import hashlib,json,subprocess

def probe(p):
 data=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(p)],text=True))
 streams=data['streams']
 if len(streams)!=1 or streams[0]['codec_type']!='video':raise ValueError('Expected silent video-only source')
 return streams[0]

def splice(base,patches,destination):
 base=Path(base);destination=Path(destination)
 if destination.exists():raise FileExistsError(destination)
 v=probe(base);total=int(v['nb_read_frames'])
 if v['r_frame_rate']!='30/1':raise ValueError('Production splice expects30fps')
 patches=sorted(patches,key=lambda x:x['start']);last=0;filters=[];labels=[];args=['ffmpeg','-v','error','-n','-i',str(base)]
 for index,p in enumerate(patches,1):
  start,end=int(p['start']),int(p['end']);q=probe(p['file'])
  if not last<=start<end<=total:raise ValueError('Invalid or overlapping frame range')
  if (q['width'],q['height'],q['r_frame_rate'],int(q['nb_read_frames']))!=(v['width'],v['height'],'30/1',end-start):raise ValueError('Patch dimensions/fps/frame count do not match range')
  args+=['-i',str(p['file'])]
  if start>last:
   label=f'b{index}';filters.append(f'[0:v]trim=start_frame={last}:end_frame={start},setpts=PTS-STARTPTS[{label}]');labels.append(label)
  label=f'p{index}';filters.append(f'[{index}:v]setpts=PTS-STARTPTS[{label}]');labels.append(label);last=end
 if last<total:
  filters.append(f'[0:v]trim=start_frame={last}:end_frame={total},setpts=PTS-STARTPTS[tail]');labels.append('tail')
 filters.append(''.join(f'[{x}]' for x in labels)+f'concat=n={len(labels)}:v=1:a=0[v]')
 destination.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run(args+['-filter_complex',';'.join(filters),'-map','[v]','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-r','30','-frames:v',str(total),'-colorspace','bt709','-color_trc','bt709','-color_primaries','bt709','-video_track_timescale','90000','-movflags','+faststart',str(destination)],check=True)
 q=probe(destination)
 if int(q['nb_read_frames'])!=total:raise ValueError('Assembled frame count changed')
 return {'frame_count':total,'fps':30,'patches':[{k:str(x[k]) for k in ['start','end','file']} for x in patches],'video_reencoded':True,'audio_handled':'none; preserve/remux verified existing soundtrack separately','sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}
