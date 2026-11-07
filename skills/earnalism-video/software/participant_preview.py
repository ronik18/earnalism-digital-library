"""A neutral first-viewing surface: no answer key, transcript or explanatory sidebar."""
from pathlib import Path
import re
from html.parser import HTMLParser

class _WithoutReviewPanels(HTMLParser):
 """Remove complete semantic panels, including nested details, without answers."""
 roles={'answer-key','speech-review','transcript-sources'}
 voids={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
 def __init__(self):super().__init__(convert_charrefs=False);self.parts=[];self.depth=0
 def handle_starttag(self,tag,attrs):
  if self.depth:
   if tag not in self.voids:self.depth+=1
  elif dict(attrs).get('data-role') in self.roles:
   if tag not in self.voids:self.depth=1
  else:self.parts.append(self.get_starttag_text())
 def handle_startendtag(self,tag,attrs):
  if not self.depth and dict(attrs).get('data-role') not in self.roles:self.parts.append(self.get_starttag_text())
 def handle_endtag(self,tag):
  if self.depth:
   if tag not in self.voids:self.depth-=1
  else:self.parts.append('</'+tag+'>')
 def handle_data(self,data):
  if not self.depth:self.parts.append(data)
 def handle_entityref(self,name):
  if not self.depth:self.parts.append('&'+name+';')
 def handle_charref(self,name):
  if not self.depth:self.parts.append('&#'+name+';')
 def handle_comment(self,data):
  if not self.depth:self.parts.append('<!--'+data+'-->')
 def handle_decl(self,decl):
  if not self.depth:self.parts.append('<!'+decl+'>')
 def handle_pi(self,data):
  if not self.depth:self.parts.append('<?'+data+'>')

def _without_review_panels(page):
 parser=_WithoutReviewPanels();parser.feed(page);parser.close()
 if parser.depth:raise ValueError('Unclosed review panel; cannot prepare a neutral participant page')
 return ''.join(parser.parts)

def make(folder):
 p=Path(folder);page=_without_review_panels((p/'watch.html').read_text())
 start=page.find('<section aria-labelledby="visual-heading">')
 if start>=0:
  end=page.index('</section>',start)+len('</section>');page=page[:start]+page[end:]
 page=re.sub(r'<nav class="links">.*?</nav>','',page,flags=re.S)
 page=re.sub(r'<p><button[^>]*>Review ending</button></p>','',page)
 # Preserve the ability to prepare older archived watch templates as well.
 markers=[page.find(m) for m in ['<details><summary>Speech review and resolutions</summary>','<details><summary>Two quick understanding checks</summary>','<details><summary>Transcript and source</summary>']]
 start=min((i for i in markers if i>=0),default=-1)
 if start>=0:
  end=page.index('</main>',start);page=page[:start]+page[end:]
 page=page.replace("let initial=null;try{const stored=sessionStorage.getItem(key);if(stored!==null)initial=Number(stored);}catch{}\nbind(video,Number.isFinite(initial)?initial:null);","bind(video,0); // Each new study viewing starts from the beginning.")
 page=page.replace('Animated explainer · Private review','Private first-viewing study · Watch once before answering')
 page=page.replace('<p class="note">Review the voice and visible animation.', '<p class="note">Please watch once without reading explanations from elsewhere. Give your answers to the facilitator before discussion.</p><p class="note">Review the voice and visible animation.')
 (p/'participant.html').write_text(page)
 # Reuse the actual independently composed portrait player and its captions.
 shorts=page.replace('max-width:100%;aspect-ratio:16/9','max-width:min(480px,42vh);aspect-ratio:9/16').replace('width="1920" height="1080" poster="landscape.png"','width="1080" height="1920" poster="portrait-captioned.png"').replace('landscape-preview.mp4?v=7','portrait-preview.mp4?v=7').replace('landscape-preview.webm?v=4','portrait-preview.webm?v=4').replace('landscape.mp4?v=4','portrait-captioned.mp4?v=4')
 shorts=shorts.replace('<main>', '<body data-portrait><main>').replace('<track kind="captions" src="captions.vtt" srclang="en" label="English" default>', '').replace('<button id="toggle-captions" type="button" aria-pressed="true">Captions: on</button>', '<button id="toggle-captions" type="button" aria-pressed="true" disabled>Captions: burned in</button>')
 (p/'participant-shorts.html').write_text(shorts)
