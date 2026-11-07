import pathlib,shutil,json,sys,subprocess
BASE=pathlib.Path(__file__).resolve().parent.parent;sys.path.insert(0,str(BASE));import studio
root=BASE/'outputs/brand-options';records=[]
original=BASE/'outputs/brand-sting-v2';first=root/'sample-1';first.mkdir(exist_ok=True)
for a,b in [('earnalism-brand-sting-master.mp4','master.mp4'),('preview.webm','preview.webm'),('poster.png','poster.png')]:
 if not (first/b).exists():shutil.copy2(original/a,first/b)
for n in (1,2,3,4):
 p=root/f'sample-{n}'
 if n>1:
  studio.run(['ffmpeg','-v','error','-n','-i',p/'render.mp4','-c:v','copy','-af','loudnorm=I=-20:TP=-2:LRA=5','-c:a','aac','-b:a','192k','-ar','48000','-t','3','-movflags','+faststart',p/'master.mp4'])
  studio.run(['ffmpeg','-v','error','-n','-i',p/'master.mp4','-c:v','libvpx-vp9','-b:v','0','-crf','24','-deadline','realtime','-cpu-used','6','-row-mt','1','-c:a','libopus','-b:a','128k',p/'preview.webm'])
  shutil.copy2(BASE/f'brand_sting/sound-provenance-{n}.json',p/'sound-provenance.json')
 r=studio.verify_media(p/'master.mp4');assert abs(r['seconds']-3)<.025
 probe=json.loads(studio.run(['ffprobe','-v','error','-show_streams','-of','json',p/'master.mp4']));v=next(s for s in probe['streams'] if s['codec_type']=='video');assert v['r_frame_rate']=='60/1' and int(v['nb_frames'])==180
 studio.run(['ffmpeg','-v','error','-i',p/'preview.webm','-f','null','-'])
 r['sample']=n;r['fps']=60;r['frames']=180;records.append(r)
 studio.run(['ffmpeg','-v','error','-n','-i',p/'master.mp4','-vf','fps=4,scale=480:-1,tile=3x4','-frames:v','1',p/'contact.png'])
studio.write(root/'technical.json',{'samples':records,'original_notebook_sha256':studio.verify_original(),'logo_sha256':studio.sha(BASE/'public/brand-sting/production-lockup.png'),'private':True})
names=['The Heritage Cover','The Opening Spread','The Silk Bookmark','The Flowing Leaf']
notes=['Burgundy hardback, gold detailing and an ivory page reveal.','An opening book unfolds into the complete brand lockup.','A burgundy ribbon draws the eye across the production logo.','Three curved paper leaves sweep away to reveal the brand.']
cards=''.join(f'<article><p class="eyebrow">SAMPLE {i+1}</p><h2>{name}</h2><video controls playsinline preload="auto" poster="sample-{i+1}/poster.png"><source src="sample-{i+1}/preview.webm" type="video/webm"><source src="sample-{i+1}/master.mp4" type="video/mp4"></video><p>{notes[i]}</p><a download href="sample-{i+1}/master.mp4">Download MP4</a></article>' for i,name in enumerate(names))
(root/'watch.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Earnalism · Four private brand introductions</title><style>*{box-sizing:border-box}body{margin:0;background:#25121a;color:#f8efdf;font:16px/1.5 system-ui}main{max-width:1450px;margin:auto;padding:36px}h1{font:clamp(30px,4vw,48px)/1.15 Georgia;margin:12px 0}h2{font:27px Georgia;margin:7px 0 20px}.eyebrow{color:#d8b67b;letter-spacing:2px;font-size:12px}.intro{max-width:760px;color:#d6c8bb}.grid{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:32px}article{background:#321b24;padding:24px;border:1px solid #a681493d;border-radius:4px}video{width:100%;aspect-ratio:16/9;background:#f6eddc}article p{color:#d6c8bb}a{color:#e3bf82}footer{margin:28px 0;color:#bdafa7;font-size:13px}@media(max-width:760px){.grid{grid-template-columns:1fr}main{padding:20px}article{padding:16px}}</style><main><p class="eyebrow">PRIVATE CREATIVE REVIEW · EARNALISM</p><h1>Four ways to open a new chapter.</h1><p class="intro">Compare the original introduction with three new directions. Each is three seconds, uses the exact production header artwork, and has its own original paper-and-music sound treatment. Play one at a time with sound on.</p><section class="grid">'''+cards+'''</section><footer>1920 × 1080 · 60 fps · H.264/AAC downloads · Private local review, not published.</footer></main><script>document.querySelectorAll('video').forEach(v=>v.addEventListener('play',()=>document.querySelectorAll('video').forEach(other=>{if(other!==v)other.pause()})));</script></html>''')
print(json.dumps(records,indent=2))
