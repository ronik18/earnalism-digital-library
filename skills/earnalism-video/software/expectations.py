"""Read-only drift preflight for owner defaults; never approves facts or media quality."""
from pathlib import Path
import json,hashlib,subprocess,argparse
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
 for key in ['asset','public_asset']:
  if digest(root/contract['brand'][key])!=contract['brand']['sha256']:issues.append('Approved brand asset changed: '+key)
 code="""import {watermarkAsset,watermarkLayout} from './src/branding.mjs';
import {assertUiClear,reviewProfileForFrame} from './src/social-safe-area.mjs';
import {subjectOpacity} from './src/opening-visibility.mjs';
import {questionHeading} from './src/readability.mjs';
const layouts=[[1920,1080],[1080,1920]].map(([width,height])=>{
 const q=watermarkLayout(width,height);let uiClear=true;
 if(height>width)try{assertUiClear('emblem',{x:q.left,y:q.top,width:q.size,height:q.size},reviewProfileForFrame(width,height));}catch{uiClear=false;}
 return {...q,width,height,uiClear};
});
console.log(JSON.stringify({asset:watermarkAsset,layouts,openingOpacity:subjectOpacity(0,0,true),question:questionHeading({heading:'Why does ice float?'})}));"""
 rendered=json.loads(subprocess.check_output(['node','--input-type=module','-e',code],cwd=root,text=True))
 if rendered['openingOpacity']!=contract['presentation_defaults']['first_frame_subject_opacity']:issues.append('Opening subject visibility drift')
 if contract['presentation_defaults']['preserve_episode_question'] and rendered['question']!='Why does ice float?':issues.append('Episode question replaced by fixed topic copy')
 if rendered['asset']['sha256']!=contract['brand']['sha256'] or rendered['asset']['crop']!=contract['brand']['crop']:issues.append('Watermark identity/crop drift')
 for q in rendered['layouts']:
  if not .35<=q['opacity']<=.5 or q['top']<0 or q['left']<0 or q['size']<=0 or q['left']+q['size']>q['width'] or q['top']+q['size']>q['height'] or not q['uiClear'] or (q['height']<=q['width'] and q['top']+q['size']>130):issues.append('Watermark restraint/clearance drift')
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
