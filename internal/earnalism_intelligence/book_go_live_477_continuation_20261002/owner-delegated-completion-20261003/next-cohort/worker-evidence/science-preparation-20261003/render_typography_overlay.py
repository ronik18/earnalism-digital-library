from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops
import hashlib,json,shutil

BASE=Path(__file__).resolve().parent
FONT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
LICENSE=Path('/usr/share/doc/fonts-dejavu-core/copyright')
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
EXPECTED={'front':'9fa719df44b5348b2dd694674fb7e4ba38438dd1e652ca70559081d67e88da15','back':'49cf4eb533e11cc92d253496e2945d700468b2a2e42b7aabf4c7d8dd3b590f09'}
META=json.loads((BASE/'root-preimage/public_book.json').read_text())
GREEN=(3,26,21)
GOLD=(239,207,116)

def centered(draw,y,text,size):
    font=ImageFont.truetype(str(FONT),size)
    box=draw.textbbox((0,0),text,font=font)
    draw.text(((1024-(box[2]-box[0]))/2-box[0],y),text,font=font,fill=GOLD)

def render(suffix):
    assets={}
    for side in ['front','back']:
        original=BASE/f'original-{side}.png';assert H(original)==EXPECTED[side]
        im=Image.open(original).convert('RGB');draw=ImageDraw.Draw(im)
        if side=='front':
            masks=[(112,85,912,680),(245,1230,784,1306)]
            draw.rounded_rectangle(masks[0],radius=30,fill=GREEN,outline=GOLD,width=3)
            centered(draw,150,'The Science',86)
            centered(draw,290,'of Getting',83)
            centered(draw,415,'Rich',134)
            draw.rectangle(masks[1],fill=GREEN)
            centered(draw,1235,META['author'],52)
        else:
            masks=[(160,1160,900,1240)]
            draw.rectangle(masks[0],fill=GREEN)
            centered(draw,1169,META['author'],60)
        diff=ImageChops.difference(im,Image.open(original).convert('RGB'))
        for rect in masks:ImageDraw.Draw(diff).rectangle(rect,fill=(0,0,0))
        assert diff.getbbox() is None, 'RGB change beyond declared masks'
        path=BASE/f'overlay-{side}-{suffix}.png';im.save(path,optimize=False,compress_level=9)
        assets[side]={'path':str(path),'sha256':H(path),'bytes':path.stat().st_size,'width':1024,'height':1536,'precise_masks':masks,'RGB_outside_masks_identical':'PASS','original_sha256':EXPECTED[side]}
    return assets

if __name__=='__main__':
    first=render('run1');second=render('run2')
    assert all(first[k]['sha256']==second[k]['sha256'] for k in first)
    shutil.copy2(LICENSE,BASE/'dejavu-font-license.txt')
    receipt={'schema':'earnalism.one-bounded-deterministic-typography-repair.v1','slug':'the-science-of-getting-rich','state':'INACTIVE_UNACCEPTED_PENDING_TWO_NEW_EXACT_REVIEWS','reason':'Original legacy title/author creation method unknown; source art retained, title and author replaced with provably deterministic existing licensed-font overlays. One art-preserving repair only.','bounded_attempt':1,'originals':json.loads((BASE/'original-cover-receipt.json').read_text())['assets'],'overlays':first,'double_render_identity':'PASS','font':{'path':str(FONT),'sha256':H(FONT),'license_path':str(BASE/'dejavu-font-license.txt'),'license_sha256':H(BASE/'dejavu-font-license.txt'),'license_basis':'Actual installed fonts-dejavu-core copyright/Bitstream Vera permission reproduced; DejaVu additions public domain; no font software modified or distributed by the Reader delivery.'},'deterministic_copy':{'title':'The Science of Getting Rich','title_rendered_lines':['The Science','of Getting','Rich'],'author':META['author']},'back_body_and_footer_original_pixels_unchanged':True,'front_art_footer_outside_title_author_masks_unchanged':True,'source_chapters_reader_versions_unchanged':True,'original_creation_method':'UNKNOWN_NOT_INFERRED','new_art':False,'paid_or_image_generation_calls':0,'new_network_requests':0,'acceptance_or_activation':False}
    (BASE/'typography-overlay-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(first,indent=2))
