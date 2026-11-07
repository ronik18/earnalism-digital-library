from pathlib import Path
import sys,json,time
sys.path.insert(0,str(Path(__file__).resolve().parent));import studio
p=studio.BASE/'outputs/moon-phases-production-review-v21';original=studio.run

def progress(args):
 if str(args[0])=='node':print('RENDER_START',str(args[-1]),time.strftime('%H:%M:%S'),flush=True)
 result=original(args)
 if str(args[0])=='node':print(result,flush=True)
 return result
studio.run=progress;studio.render(p,frozen=True)
print('CLEAN_PRIVATE_RENDER_COMPLETE',json.dumps(studio.load(p/'technical.json')),flush=True)
