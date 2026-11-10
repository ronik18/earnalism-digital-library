#!/usr/bin/env python3
"""Inspect the exact Instagram upload MP4; never certifies mobile rendering."""
import argparse, hashlib, json, struct, subprocess, sys
from pathlib import Path

def validate_report_path(report, *media):
    report=Path(report)
    # Conservative case-folding also covers a not-yet-created derivative on
    # the owner's case-insensitive filesystem; no media path may become JSON.
    if any(str(report.resolve()).casefold()==str(Path(path).resolve()).casefold() for path in media):
        raise ValueError('Report must not alias a source or derivative media path')
    if report.exists() or report.is_symlink():
        raise ValueError('Existing report or report symlink is preserved; choose a new path')
    if not report.parent.is_dir():
        raise ValueError('Report parent directory must already exist')
    return report

def boxes(data, start=0, end=None):
    end = len(data) if end is None else end
    out=[]
    while start < end:
        if end-start < 8: raise ValueError('Truncated MP4 box header')
        size,kind=struct.unpack_from('>I4s',data,start); header=8
        if size==1:
            if end-start < 16: raise ValueError('Truncated extended box')
            size=struct.unpack_from('>Q',data,start+8)[0];header=16
        if size==0:size=end-start
        if size<header or start+size>end:raise ValueError('Invalid/truncated MP4 box')
        name=kind.decode('ascii',errors='replace');out.append((name,start,size))
        if kind in (b'moov',b'trak',b'edts',b'mdia',b'minf',b'stbl'):
            out.extend(boxes(data,start+header,start+size))
        start+=size
    return out

def inspect(path):
    data=path.read_bytes(); atom=boxes(data)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    audio=next((s for s in probe['streams'] if s['codec_type']=='audio'),{})
    issues=[]
    if video['codec_name']!='h264' or video.get('pix_fmt')!='yuv420p':issues.append('Expected H.264 8-bit 4:2:0')
    if video.get('field_order') not in ('progressive','unknown'):issues.append('Non-progressive source')
    if (video['width'],video['height']) not in ((1080,1920),(720,1280)):issues.append('Review portrait dimensions; do not silently upscale')
    if any(n=='elst' for n,_,_ in atom):issues.append('MP4 edit lists present: prepare separate no-edit-list Instagram derivative and verify sync')
    moov=next((p for n,p,_ in atom if n=='moov'),None);mdat=next((p for n,p,_ in atom if n=='mdat'),None)
    if moov is None or mdat is None or moov>mdat:issues.append('Missing fast-start moov before mdat')
    if audio.get('codec_name')!='aac' or int(audio.get('sample_rate',0))>48000:issues.append('Review AAC/sample rate')
    decode=subprocess.run(['ffmpeg','-v','error','-xerror','-err_detect','explode','-i',str(path),'-map','0:v:0','-map','0:a:0','-f','null','-'],capture_output=True,text=True)
    if decode.returncode or decode.stderr.strip():issues.append('Strict full decode failed or emitted errors')
    return {'file':str(path),'sha256':hashlib.sha256(data).hexdigest(),'state':'REVIEW_REQUIRED' if issues else 'TECHNICAL_CHECKS_PASS_NOT_MOBILE_ACCEPTANCE','issues':issues,'video':{k:video.get(k) for k in ('codec_name','profile','level','pix_fmt','width','height','field_order','r_frame_rate','avg_frame_rate','start_time','duration')},'audio':{k:audio.get(k) for k in ('codec_name','profile','sample_rate','channels','start_time','duration')},'edit_list_count':sum(n=='elst' for n,_,_ in atom),'decode_returncode':decode.returncode,'decode_errors':decode.stderr[-4000:],'not_proven':['No visual corruption on all decoded frames','Closed GOP compliance','Android/native Instagram rendition and playback','Root cause or permanent platform fix']}
def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('input',type=Path);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args(argv)
    try:
        report=validate_report_path(args.report,args.input)
        # Reserve a new inode before processing. A racing file/symlink cannot
        # redirect either the success report or an error report onto media.
        with report.open('x',encoding='utf-8') as output:
            try:result=inspect(args.input)
            except (OSError,ValueError,StopIteration,subprocess.SubprocessError) as e:result={'state':'FAIL','error':str(e)}
            output.write(json.dumps(result,indent=2)+'\n')
    except (OSError,ValueError) as e:
        print('Report path refused: '+str(e),file=sys.stderr);return 2
    print(result['state'])
    return 0 if result['state'].startswith('TECHNICAL') else 2

if __name__=='__main__':
    raise SystemExit(main())
