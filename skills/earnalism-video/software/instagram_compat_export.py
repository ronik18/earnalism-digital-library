#!/usr/bin/env python3
"""Private Instagram derivative for reproduced 1080p Android preview tearing.
Keeps AAC packets; verifies original decoded PCM, content-frame count and A/V shift.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

def validate_report_path(report,*media):
 report=Path(report)
 # Include not-yet-created case aliases on case-insensitive filesystems.
 if any(str(report.resolve()).casefold()==str(Path(path).resolve()).casefold() for path in media):
  raise ValueError('Report must not alias a source or derivative media path')
 if report.exists() or report.is_symlink():
  raise ValueError('Existing report or report symlink is preserved; choose a new path')
 if not report.parent.is_dir():
  raise ValueError('Report parent directory must already exist')
 return report

def run(cmd):return subprocess.check_output(cmd)
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_streams','-of','json',str(p)]))['streams']
def frames(p):return json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(p)]))['frames']
def pcm(p):return run(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-f','f32le','-'])
def payload(p):return run(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-']).decode().strip()
def export(source,target):
 if source.resolve()==target.resolve() or target.exists():raise ValueError('Never overwrite source or existing derivative')
 ss=probe(source);v=next(s for s in ss if s['codec_type']=='video');a=next(s for s in ss if s['codec_type']=='audio')
 if (v['width'],v['height'])!=(1080,1920) or v['r_frame_rate']!='30/1':raise ValueError('This tested profile expects reviewed 1080x1920 30fps portrait')
 if a['codec_name']!='aac' or int(a['sample_rate'])!=48000 or a['channels']!=2:raise ValueError('This tested profile expects existing AAC stereo 48k; do not silently regenerate audio')
 cmd=['ffmpeg','-v','error','-i',str(source),'-map','0:v:0','-map','0:a:0','-vf','scale=720:1280:flags=lanczos,setsar=1','-c:v','libx264','-preset','fast','-crf','18','-profile:v','high','-level:v','4.0','-pix_fmt','yuv420p','-bf','0','-g','60','-keyint_min','60','-sc_threshold','0','-x264-params','open-gop=0','-c:a','copy','-use_editlist','0','-avoid_negative_ts','make_zero','-movflags','+faststart','-n',str(target)]
 subprocess.run(cmd,check=True)
 original,derived=pcm(source),pcm(target);stride=8
 # Locate exact original PCM, allowing only a bounded AAC priming prefix.
 anchor=original[48000*stride:48000*stride+16000];at=derived.find(anchor);offset=at-48000*stride
 pcm_ok=0<=offset<=2048*stride and offset%stride==0 and derived[offset:]==original
 af,bf=frames(source),frames(target);shift=offset/stride/48000 if pcm_ok else None
 deltas=[float(y['best_effort_timestamp_time'])-float(x['best_effort_timestamp_time']) for x,y in zip(af[1:],bf[1:])]
 av_error=max(abs(d-shift) for d in deltas) if shift is not None else None
 packet_ok=payload(source)==payload(target)
 good=pcm_ok and packet_ok and len(af)==len(bf) and av_error is not None and av_error<0.001
 return {'state':'TECHNICALLY_VERIFIED_PRIVATE_NATIVE_REVIEW_REQUIRED' if good else 'HOLD','source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'file':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'dimensions':[720,1280],'audio_packet_payload_identical':packet_ok,'original_decoded_pcm_identical_after_priming':pcm_ok,'priming_samples':offset//stride if pcm_ok else None,'source_frames':len(af),'candidate_frames':len(bf),'maximum_relative_av_shift_seconds':av_error,'private':True,'native_preview':'PENDING exact-file review','publication_authority':False,'note':'First video frame holds through AAC priming; later content and burned captions share that shift. No narration/score edits or audio re-encoding. Retain 1080p master. Not a universal device fix.'}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('target',type=Path);p.add_argument('--report',required=True,type=Path);args=p.parse_args(argv)
 try:
  report=validate_report_path(args.report,args.source,args.target)
  with report.open('x',encoding='utf-8') as output:
   try:r=export(args.source,args.target)
   except (OSError,ValueError,StopIteration,subprocess.SubprocessError) as e:r={'state':'HOLD','error':str(e),'private':True}
   output.write(json.dumps(r,indent=2)+'\n')
 except (OSError,ValueError) as e:
  print('Report path refused: '+str(e),file=sys.stderr);return 2
 print(r['state']);return 0 if r['state'].startswith('TECHNICALLY') else 2

if __name__=='__main__':
 raise SystemExit(main())
