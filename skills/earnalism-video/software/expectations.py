"""Read-only drift preflight for owner defaults; never approves facts or media quality."""
from pathlib import Path
import json,hashlib,subprocess,argparse,math
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class Preview(HTMLParser):
 def __init__(self):super().__init__();self.download_links=[];self.videos=[];self.ids=set()
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'download' in a:self.download_links.append(a)
  if tag=='video':self.videos.append(a)
  if 'id' in a:self.ids.add(a['id'])
def audit(root=ROOT):
 root=Path(root);contract=json.loads((root/'config/editorial-contract.json').read_text());policy=json.loads((root/'config/defaults.json').read_text());issues=[]
 if contract.get('schema')!='earnalism.editorial-contract.v1':raise ValueError('Unknown editorial contract')
 for key,value in contract['defaults'].items():
  if policy.get(key)!=value:issues.append('Default drift: '+key)
 voice=policy.get('voice_profiles',{}).get(contract['defaults']['default_voice_profile'],{})
 if voice.get('selected_audition_sha256')!=contract['voice_selection']['audition_sha256']:issues.append('Selected voice baseline binding changed')
 if hashlib.sha256(voice.get('instruction','').encode()).hexdigest()!=contract['voice_selection']['instruction_sha256']:issues.append('Selected voice baseline instruction changed')
 if policy.get('instruction')!=voice.get('instruction'):issues.append('Default narration direction diverges from selected voice baseline')
 if contract['voice_selection'].get('selection_kind')=='refinement_baseline':
  if voice.get('selection_kind')!='refinement_baseline':issues.append('Refinement baseline scope changed')
  if any(voice.get(key) is not False or contract['voice_selection'].get(key) is not False for key in ('recording_acceptance','publication_approval')):issues.append('Refinement baseline cannot imply repaired-recording or publication approval')
 if policy.get('voice_delivery',{}).get('pitch_shift') is not False:issues.append('Pitch-shift default is not disabled')
 for key,value in contract['brand']['outro'].items():
  if policy.get('intro',{}).get(key)!=value:issues.append('Brand ending drift: '+key)
 if policy.get('music',{}).get('palette')!=contract['music']['moon_palette']:issues.append('Moon score default drift')
 # Future treatment is explicit. Historical palettes/adapters gain no new
 # full-body coverage or media approval merely by passing this drift audit.
 future={'id':'continuous_open_instrumental_v1','instrumental':True,
  'commercially_cleared_open_license':True,'coverage':'main-video-start-through-main-video-end',
  'intentional_silent_body_sections':False,'boundary_fades':'gentle-boundary-only',
  'mood':'calm-focus-relaxation','efficacy_claims':False,'narrator_clear':True,
  'narration_waveform_unchanged':True,'body_music_bleed_into_end_ident':False,
  'qualified_by_configuration_alone':False}
 for label,record in [('Policy',policy.get('music',{})),('Contract',contract.get('music',{}))]:
  if record.get('future_profile')!=future:issues.append(label+' future music profile drift')
  if record.get('legacy_palette_scope')!='historical-candidate-bindings-only-not-future-treatment':issues.append(label+' historical palette scope drift')
 ending={'enabled':True,'version':'earnalism-flowing-paired-v1','seconds':3,'placement':'end',
  'preserve_approved_video_frames':True,'preserve_approved_own_audio_samples':True,
  'body_music_bleed':False,'duration_frames_30fps':90,'audio_samples_48khz':144000}
 for label,record in [('Policy',policy.get('intro',{})),('Contract',contract.get('brand',{}).get('outro',{}))]:
  if any(record.get(k)!=v for k,v in ending.items()):issues.append(label+' exact END treatment drift')
 for key in ['asset','public_asset']:
  if digest(root/contract['brand'][key])!=contract['brand']['sha256']:issues.append('Approved brand asset changed: '+key)
 code="""import {watermarkAsset,watermarkLayout} from './src/branding.mjs';
import {assertUiClear,reviewProfileForFrame,safeContentRect,portraitReviewProfile,landscapeReviewProfile} from './src/social-safe-area.mjs';
import {subjectOpacity} from './src/opening-visibility.mjs';
import {questionHeading} from './src/readability.mjs';
const layouts=[[1920,1080],[1080,1920]].map(([width,height])=>{
 const q=watermarkLayout(width,height),profile=reviewProfileForFrame(width,height,height>width?portraitReviewProfile:landscapeReviewProfile),safe=safeContentRect(profile);let uiClear=true;
 try{assertUiClear('complete logo and blur halo',q.protectedRect,profile);}catch{uiClear=false;}
 const atTopRight=!!q.protectedRect&&Math.abs(q.protectedRect.y-safe.y)<1e-8&&Math.abs(q.protectedRect.x+q.protectedRect.width-safe.x-safe.width)<1e-8;
 return {...q,frameWidth:width,frameHeight:height,uiClear,atTopRight};
});
const covers=[[1920,1080],[1080,1920]].map(([w,h])=>watermarkLayout(w,h,{surface:'cover'}).blurPx);
console.log(JSON.stringify({asset:watermarkAsset,layouts,covers,openingOpacity:subjectOpacity(0,0,true),question:questionHeading({heading:'Why does ice float?'})}));"""
 rendered=json.loads(subprocess.check_output(['node','--input-type=module','-e',code],cwd=root,text=True))
 if rendered['openingOpacity']!=contract['presentation_defaults']['first_frame_subject_opacity']:issues.append('Opening subject visibility drift')
 if contract['presentation_defaults']['preserve_episode_question'] and rendered['question']!='Why does ice float?':issues.append('Episode question replaced by fixed topic copy')
 if rendered['asset']['sha256']!=contract['brand']['sha256'] or rendered['asset']['crop']!=contract['brand']['crop']:issues.append('Watermark identity/crop drift')
 for q in rendered['layouts']:
  if not all(isinstance(q.get(k),(int,float)) for k in ('opacity','top','left','width','height')) or not q.get('uiClear'):
   issues.append('Full watermark identity/clearance drift');continue
  if not .5<=q['opacity']<=1 or q['top']<0 or q['left']<0 or q['width']<=0 or q['height']<=0 or q['left']+q['width']>q['frameWidth'] or q['top']+q['height']>q['frameHeight'] or abs(q['width']/q['height']-2400/720)>.001:issues.append('Full watermark identity/clearance drift')
  style=contract['brand'].get('watermark_style',{})
  if style.get('anchor')!='top-right-destination-safe' or not q.get('atTopRight') or q.get('blurPx')!=style.get('blur_px_at_1080p') or q.get('blurOutset')!=math.ceil(style.get('blur_support_sigma',0)*q.get('blurPx',0)) or not all(style.get(k) is True for k in ('full_lockup','video_only','covers_unchanged','end_ident_unchanged')):issues.append('Watermark styling/anchor drift')
 if rendered['covers']!=[0,0]:issues.append('Cover watermark styling changed')
 component=(root/'src/BrandWatermark.tsx').read_text()
 if 'filter:q.blurPx>0?' not in component or 'blur(${q.blurPx}px)' not in component:issues.append('Shared watermark blur is not applied to the full image')
 page=(root/'watch-template.html').read_text();html=Preview();html.feed(page)
 if html.download_links:issues.append('Visible download link restored')
 if not html.videos or any('nodownload' not in v.get('controlslist','').split() for v in html.videos):issues.append('Download UI hint missing')
 if not {'replay-preview','caption-safe-area','fullscreen-preview','reload-preview'}.issubset(html.ids):issues.append('Required accessible review controls missing')
 if '{{SOURCES}}' not in page or '{{DISCLOSURE}}' not in page:issues.append('Source/disclosure access missing')
 report={'status':'FAIL' if issues else 'PASS','scope':'Owner-default, approved-asset and review-control drift only; not factual, graphical, listening or publication approval','contract_sha256':digest(root/'config/editorial-contract.json'),'issues':issues,'human_approvals_supplied':False}
 if issues:raise ValueError('; '.join(issues))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(ROOT));a=p.parse_args();print(json.dumps(audit(a.root),indent=2))
