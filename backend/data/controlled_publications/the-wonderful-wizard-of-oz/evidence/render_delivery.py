from pathlib import Path
from PIL import Image
import json,hashlib,sys
BASE=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else BASE/'delivery-verification'
OUT.mkdir(parents=True,exist_ok=True)
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SOURCES={'front':'80fbd30875f8b715fb580732f9eef2d46bc7ddc74d50cd41d5276dbfd60ec32a','back':'29204906556020adbbdb10a89b7fd9b26f08703f6327a0de63cdb0d50b8821fc'}
assets={}
for side in ['front','back']:
 source=BASE/f'original-{side}.png';assert H(source)==SOURCES[side]
 p=OUT/f'{side}-delivery.webp';Image.open(source).convert('RGB').resize((500,750),Image.Resampling.LANCZOS).save(p,'WEBP',quality=45,method=6)
 Image.open(p).load();assert p.stat().st_size<=80000
 assets[side]={'source_sha256':H(source),'path':str(p),'sha256':H(p),'bytes':p.stat().st_size,'width':500,'height':750,'url':f'/assets/books/the-wonderful-wizard-of-oz/{side}-{H(p)[:8]}.webp'}
print(json.dumps(assets,indent=2))
if OUT==BASE/'delivery':
 (BASE/'delivery-receipt.json').write_text(json.dumps({'schema':'earnalism.cover-delivery-derivation.v1','slug':'the-wonderful-wizard-of-oz','state':'INACTIVE_UNACCEPTED_PENDING_TWO_NEW_EXACT_REVIEWS','assets':assets,'recipe':'Original exactRGB owner PNG→500x750LANCZOSWebPquality45method6; fullframe no crop/no newart/no copychange','renderer_sha256':H(Path(__file__)),'card_budget_bytes':80000,'paid_calls':0,'art_repairs':0,'acceptance_or_activation':False},ensure_ascii=False,indent=2)+'\n')
