from pathlib import Path
import sys,json,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import studio
from pace_review import review,compare_scene_rates
p=studio.BASE/'outputs/moon-teacher-transitions-v9-final';ep=studio.load(p/'episode.json');policy=studio.load(studio.BASE/'config/defaults.json')['pace_review']
reports=[{'scene':s['id'],**review(studio.load(p/'alignment'/(s['id']+'.json')),p/'raw'/(s['id']+'.wav'),s['text'],policy)} for s in ep['scenes']]
studio.write(p/'pre-render-pace-review.json',{'scenes':reports,'consistency':compare_scene_rates(reports),'human_listening_review':'PENDING'})
if any(r['flags'] for r in reports):raise RuntimeError('Inspect pace flags before rendering')
original=studio.run
def progress(args):
 if str(args[0])=='node':print('RENDER_START',str(args[-1]),time.strftime('%H:%M:%S'),flush=True)
 result=original(args)
 if str(args[0])=='node':print(result,flush=True)
 return result
studio.run=progress
studio.render(p);print('PRIVATE_RENDER_COMPLETE',json.dumps(studio.load(p/'technical.json')),flush=True)
