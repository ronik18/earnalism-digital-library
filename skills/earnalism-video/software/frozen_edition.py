"""Fresh clean production-review draft from researched content and frozen licensed assets.
Original private fixtures remain immutable and cannot publish. No approvals transfer.
"""
from pathlib import Path
import shutil,json
import studio
from audio_derivation import check_unit
from learning_acceptance import pending
FROZEN=('narration.wav','mix.wav','score.wav','score-ducked.wav','captions.srt','captions.vtt','transcript.txt')
def verify(folder):
 folder=Path(folder);record=studio.load(folder/'frozen-assets.json')
 for name,digest in record['files'].items():
  if studio.sha(folder/name)!=digest:raise ValueError('Frozen audio/caption changed: '+name)
 ep=studio.validate(studio.load(folder/'episode.json'))
 for scene in ep['scenes']:
  check_unit(folder,scene['id']);asr=studio.load(folder/'alignment'/(scene['id']+'.json'))
  if asr.get('unresolved_asr_edits') or asr['audio_sha256']!=studio.sha(folder/'raw'/(scene['id']+'.wav')):raise ValueError('Changed source alignment')
  from asr_review import require_script_match
  require_script_match(asr,scene['text'])
 props=studio.load(folder/'props.json')
 if props.get('duration')!=record['body_seconds'] or props.get('reviewOverlay') is not False:raise ValueError('Frozen timing or clean review classification changed')
 return props

def prepare(source,destination):
 source=Path(source).resolve();dest=Path(destination).resolve()
 if dest.exists():raise FileExistsError(dest)
 studio.verify_original();manifest=studio.load(source/'delivery-manifest.json')
 if any(studio.sha(source/n)!=h for n,h in manifest.items()):raise ValueError('Source manifest changed')
 from audience_plan import referenced_assets
 preserved_assets=referenced_assets(source)
 excluded={'compare.html','quality-evidence','viewer-study.json','youtube-landscape.json','youtube-shorts.json','publication-handoff.json','production-journal.jsonl','strict-quality-review.json','logs','qa','frozen-assets.json','frozen-audio-delivery.json','participant.html','participant-shorts.html','episode.json','props.json','caption-props.json','review.json','acceptance-review.json','delivery-manifest.json','technical.json','rights-audit.json','watch.html','portrait-short.html','youtube.json','remix-provenance.json','renderer-source-manifest.json','intro-and-dry-narration.wav'}
 shutil.copytree(source,dest,ignore=lambda path,names:[n for n in names if n in excluded or Path(n).suffix in ('.mp4','.webm') or (Path(n).suffix=='.png' and str((Path(path)/n).relative_to(source)) not in preserved_assets)])
 old=studio.load(source/'episode.json')
 ep={k:v for k,v in old.items() if k not in ('id','private_test','status','voice_selection')}
 ep.update({'id':dest.name,'private_test':False,'status':'production-draft-private','production_candidate':True,'requires_learning_acceptance':True,'voice_selection':{**old.get('voice_selection',{}),'recording_approval':'PENDING for this exact clean edition'},'qualification':'Fresh production-review render from researched Moon content and frozen licensed source assets; not a relabelled fixture or publication approval.'})
 from strict_quality import pending as pending_strict
 studio.write(dest/'strict-quality-review.json',pending_strict())
 studio.write(dest/'episode.json',ep);studio.write(dest/'youtube.json',studio.youtube_metadata(ep));studio.write(dest/'review.json',{'reviewer':'','delivery_manifest_sha256':None,**{k:False for k in ('factual','rights','voice','audiovisual','technical','delivery')},'note':'New clean production-review draft. Every approval pending; no fixture approval transfers.'});studio.write(dest/'acceptance-review.json',pending(previous=studio.load(source/'acceptance-review.json') if (source/'acceptance-review.json').exists() else None))
 props=studio.load(source/'props.json');props.update({'reviewOverlay':False,'burnCaptions':False})
 public=studio.BASE/'public/runs'/dest.name;public.mkdir(parents=True)
 from intro import install
 props['intro'],brand=install(public,studio.BASE/'assets/standard-intro/v1','earnalism-flowing-paired-v1');props['intro']['placement']='end'
 shutil.copy2(dest/'mix.wav',public/'mix.wav');props['audio']=f'runs/{dest.name}/mix.wav';studio.write(dest/'props.json',props)
 studio.write(dest/'frozen-assets.json',{'source_private_edition':source.name,'source_manifest_sha256':studio.sha(source/'delivery-manifest.json'),'body_seconds':props['duration'],'files':{n:studio.sha(source/n) for n in FROZEN},'no_synthesis_or_audio_processing':True,'source_approval_transferred':False})
 from audience_plan import initialize as initialize_audience
 initialize_audience(dest)
 verify(dest);return dest
if __name__=='__main__':
 import sys
 print(prepare(sys.argv[1],sys.argv[2]))

def encoded_audio_hash(path):
 import subprocess,hashlib
 return hashlib.sha256(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-c','copy','-f','adts','-'])).hexdigest()

def copy_frozen_soundtrack(folder,output):
 """Keep the exact reviewed AAC packets; only fresh clean video is retained."""
 import subprocess
 folder=Path(folder);output=Path(output);record=studio.load(folder/'frozen-assets.json');source=studio.BASE/'outputs'/record['source_private_edition']
 if studio.sha(source/'delivery-manifest.json')!=record['source_manifest_sha256']:raise ValueError('Frozen source manifest changed')
 manifest=studio.load(source/'delivery-manifest.json');reference=source/'landscape.mp4'
 if studio.sha(reference)!=manifest['landscape.mp4']:raise ValueError('Frozen encoded soundtrack source changed')
 archive=folder/'logs/pre-frozen-audio';archive.mkdir(parents=True,exist_ok=True);original=archive/output.name
 if original.exists():raise FileExistsError(original)
 output.rename(original)
 subprocess.run(['ffmpeg','-v','error','-n','-i',str(original),'-i',str(reference),'-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',str(output)],check=True)
 expected=encoded_audio_hash(reference)
 if encoded_audio_hash(output)!=expected:raise ValueError('Frozen AAC payload changed')
 return {'source':source.name,'encoded_audio_sha256':expected,'audio_stream_copied':True}
