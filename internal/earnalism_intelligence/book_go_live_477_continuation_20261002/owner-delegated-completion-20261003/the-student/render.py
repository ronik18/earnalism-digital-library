from pathlib import Path
import hashlib, json
from PIL import Image, ImageDraw, ImageFont, ImageChops

BASE = Path(__file__).resolve().parent
REPO = Path('/tmp/earnalism-main-approved-integration')
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
META = json.loads((BASE/'preserved-preimage/public_book.json').read_text())
H = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
MAROON = (66, 22, 30, 255)
GOLD = (223, 183, 92, 255)
CREAM = (246, 231, 189, 255)

def centered(draw, y, text, size, fill=CREAM):
    font = ImageFont.truetype(str(FONT), size)
    box = draw.textbbox((0,0), text, font=font)
    x = (1600-(box[2]-box[0]))/2-box[0]
    draw.text((x,y),text,font=font,fill=fill)

def lines(text, max_width, size):
    font=ImageFont.truetype(str(FONT),size)
    draw=ImageDraw.Draw(Image.new('RGB',(1,1)))
    result=[]; line=''
    for word in text.split():
        attempt=(line+' '+word).strip()
        if draw.textlength(attempt,font=font)>max_width:
            result.append(line);line=word
        else: line=attempt
    if line:result.append(line)
    return result

def render(suffix):
    out={}
    for kind,name in [('front','the-student-cover_url.png'),('back','the-student-back_cover_url.png')]:
        im=Image.open(BASE/name).convert('RGBA');draw=ImageDraw.Draw(im)
        if kind=='front':
            # New layout-only repair: maintain original art beyond explicit masks.
            draw.rounded_rectangle((215,705,1385,1265),radius=42,fill=MAROON,outline=GOLD,width=5)
            centered(draw,835,META['title'],118)
            draw.line((480,1045,1120,1045),fill=GOLD,width=3)
            centered(draw,1090,META['author'],59)
            draw.rounded_rectangle((180,1830,1420,2140),radius=30,fill=MAROON)
            masks=[(215,705,1385,1265),(180,1830,1420,2140)]
        else:
            # Entire old incomplete copy and intersecting ornaments are masked.
            draw.rounded_rectangle((95,70,1505,2160),radius=52,fill=MAROON)
            draw.rounded_rectangle((125,70,1475,2160),radius=52,outline=GOLD,width=5)
            centered(draw,160,'BACK COVER',43,GOLD)
            centered(draw,315,META['title'],110)
            centered(draw,480,META['author'],58)
            draw.line((320,625,1280,625),fill=GOLD,width=3)
            y=730
            for field in ['short_description','description']:
                for line in lines(META[field],1120,47):
                    centered(draw,y,line,47);y+=78
                y+=65
            assert y < 2040, y
            masks=[(95,70,1505,2160)]
        path=BASE/f'candidate-{kind}-{suffix}.png';im.save(path,optimize=False,compress_level=9)
        original=Image.open(BASE/name).convert('RGBA')
        diff=ImageChops.difference(im,original)
        for rect in masks: ImageDraw.Draw(diff).rectangle(rect,fill=(0,0,0,0))
        assert diff.getbbox() is None
        out[kind]={'path':str(path),'sha256':H(path),'bytes':path.stat().st_size,'width':1600,'height':2400,'changed_region_rectangles':masks,'unchanged_pixels_outside_masks':'PASS'}
    return out

if __name__=='__main__':
    original_expected={'front':'852b0ec54f013b2c24c63514e21d524ea7b42fc1151de16f5ecbc7aa624825db','back':'c48024e8f29f6efdf32474199e4178a477bde4c6bd5624eb619bf911fdb9da25'}
    originals={}
    for kind,name in [('front','the-student-cover_url.png'),('back','the-student-back_cover_url.png')]:
        p=BASE/name; assert H(p)==original_expected[kind]
        originals[kind]={'path':str(p),'sha256':H(p),'url':META['cover_url' if kind=='front' else 'back_cover_url'],'bytes':p.stat().st_size,'width':1600,'height':2400}
    run1=render('run1');run2=render('run2')
    assert all(run1[k]['sha256']==run2[k]['sha256'] for k in run1)
    receipt={'schema':'earnalism.inactive-cover-derivative-receipt.v1','slug':'the-student','created_on':'2026-10-03','state':'INACTIVE_NEW_CANDIDATE_PENDING_TWO_NEW_VISUAL_AND_PACKAGE_REVIEWS','method':'One bounded deterministic local mask-and-typeset layout-only remediation from verified owner originals; no image generation or paid call','originals':originals,'renders':run1,'double_render_byte_identity':'PASS','font_files':{'serif':{'path':str(FONT),'sha256':H(FONT)}},'copy':{k:META[k] for k in ['title','author','short_description','description']},'copy_basis':'Exact existing public_book metadata; no new text claims','originals_unchanged':True,'previous_reviewed_derivatives':'Unavailable after restore; historical reviews do not apply to this new candidate','network_fetches':0,'paid_generation':0,'cover_display_approved':False,'publication_approved':False,'production_activation_authorized':False,'audio_authorized':False,'production_observed':False,'owner_declaration':{'path':'internal/legal/bengali_text_preparation_20261002/evidence_matrix.json','sha256':H(REPO/'internal/legal/bengali_text_preparation_20261002/evidence_matrix.json'),'statement':'Owner states all front and back covers are designed by the owner.'}}
    (BASE/'candidate-cover-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(run1,indent=2))
