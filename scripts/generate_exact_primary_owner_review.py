#!/usr/bin/env python3
"""Generate a visual owner-review package from local, deterministic captures."""
from __future__ import annotations
import datetime, hashlib, json, mimetypes, os, shutil, subprocess, zipfile
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(".").resolve()
WORK = Path(os.environ.get("EXACT_OWNER_REVIEW_WORK_DIR", ROOT / "uat/evidence/exact-primary-design")).resolve()
OUT = WORK / "owner-review-final"
REFERENCE = ROOT / "docs/design-references"
BOARD_ONE = REFERENCE / "home-library-commerce-desktop.png"
BOARD_TWO = REFERENCE / "reader-listener-bookdetail-desktop.png"
CROPS = {
 "home-desktop": (10,18,540,747,BOARD_ONE), "library-desktop": (560,18,518,747,BOARD_ONE), "commerce-desktop": (1088,18,438,750,BOARD_ONE),
 "home-mobile": (24,792,198,232,BOARD_ONE), "library-mobile": (265,792,222,232,BOARD_ONE), "library-filter-mobile": (1325,792,205,232,BOARD_ONE), "commerce-mobile": (793,792,193,232,BOARD_ONE), "reading-pass-mobile": (793,792,193,232,BOARD_ONE), "mobile-navigation": (1017,792,255,232,BOARD_ONE),
 "book-detail-desktop": (1080,22,443,495,BOARD_TWO), "reader-desktop": (11,22,566,495,BOARD_TWO), "listener-desktop": (590,22,477,495,BOARD_TWO),
 "book-detail-mobile": (399,568,180,352,BOARD_TWO), "reader-mobile": (11,568,186,352,BOARD_TWO), "listener-mobile": (202,568,177,352,BOARD_TWO), "about-mobile": (1352,568,170,352,BOARD_TWO), "my-library-mobile": (969,568,180,352,BOARD_TWO), "profile-mobile": (1170,568,170,352,BOARD_TWO),
}
OVERRIDES = {"reader-desktop":"PRODUCT_TRUTH_OVERRIDE: visual fixture only; production access remains fail-closed.", "reader-mobile":"PRODUCT_TRUTH_OVERRIDE: visual fixture only; production access remains fail-closed.", "listener-desktop":"PRODUCT_TRUTH_OVERRIDE: review fixture has no audio URL or playback; production requires an active Reading Pass.", "listener-mobile":"PRODUCT_TRUTH_OVERRIDE: review fixture has no audio URL or playback; production requires an active Reading Pass.", "commerce-desktop":"DYNAMIC_REAL_DATA: deterministic server-contract offer fixture, not a promise of a fixed configured price.", "commerce-mobile":"DYNAMIC_REAL_DATA: deterministic server-contract offer fixture, not a promise of a fixed configured price."}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
def crop(state):
 x,y,w,h,board=CROPS[state]; image=Image.open(board).convert("RGB"); return image.crop((x,y,x+w,y+h)), board
def maybe(path): return path if path.exists() else None
def diff(reference, current):
 current=current.convert("RGB").resize(reference.size, Image.Resampling.LANCZOS)
 return ImageChops.difference(reference, current).point(lambda x:min(255,x*4)), Image.blend(reference, current, .5)
def load(path): return json.loads(path.read_text()) if path.exists() else {"states":[]}
def current_head():
 return os.environ.get("GITHUB_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
CORRECTIONS = {
 "D01":"One canonical responsive shell, readable branding, and font verification.",
 "D02":"Home hero, journey heading, discovery shelf, and mobile hierarchy.",
 "D03":"Library title, controls, filter rail, shelves, and mobile density.",
 "D04":"Full-viewport mobile navigation and filter overlays with inert background.",
 "D05":"Single-column Commerce desktop composition without research rail.",
 "D06":"Plan-first mobile Pricing/Reading Pass composition.",
 "D07":"Compact Book Detail identity and action composition.",
 "D08":"Reader typography control and non-redundant mobile controls.",
 "D09":"Listener cover-led layout using metadata cover contract; no CSS-painted cover.",
 "D10":"About rhythm and truthful one-header My Library/Profile compositions.",
}

def main():
 OUT.mkdir(parents=True, exist_ok=True)
 current_dir=WORK/"current"; before_dir=WORK/"before"
 current={x["id"]:x for x in load(current_dir/"capture.json").get("states",[])}; before={x["id"]:x for x in load(before_dir/"capture.json").get("states",[])}
 records=[]; pages=[]
 for state in CROPS:
  ref, board=crop(state); ref_name=f"{state}-reference.png"; ref.save(OUT/ref_name)
  current_path=maybe(current_dir/f"{state}.png"); before_path=maybe(before_dir/f"{state}.png")
  current_name=f"{state}-current.png"; before_name=f"{state}-before.png"
  if current_path: shutil.copy2(current_path, OUT/current_name)
  if before_path: shutil.copy2(before_path, OUT/before_name)
  heat_name=f"{state}-heatmap.png"; overlay_name=f"{state}-overlay.png"
  if current_path:
   heat, overlay=diff(ref,Image.open(current_path)); heat.save(OUT/heat_name); overlay.save(OUT/overlay_name)
  record={"state":state,"reference_board":board.name,"reference_sha256":sha(board),"reference_crop":{"x":CROPS[state][0],"y":CROPS[state][1],"width":CROPS[state][2],"height":CROPS[state][3]},"current_capture":current.get(state,{}),"before_capture":before.get(state,{}),"labels":["EXACT_REFERENCED_REGION","RESPONSIVE_EXTRAPOLATION","DYNAMIC_REAL_DATA"],"product_truth_override":OVERRIDES.get(state,"None"),"source_asset_limitation":"Listener cover remains supplied by current approved release artwork; no embedded UI is used as an asset." if state.startswith("listener") else "None"}
  records.append(record)
  page=Image.new("RGB",(1600,1100),"#f6f1e8"); draw=ImageDraw.Draw(page); font=ImageFont.load_default(); draw.text((32,24),f"{state} | EXACT REFERENCED REGION / CURRENT ROUTED UI",fill="#142019",font=font); draw.text((32,46),record["product_truth_override"],fill="#6a5121",font=font)
  left=ref.copy(); left.thumbnail((720,970)); page.paste(left,(32,95))
  if current_path:
   right=Image.open(current_path).convert("RGB"); right.thumbnail((720,970)); page.paste(right,(830,95))
  pages.append(page)
 head=current_head()
 score_report={"schema_version":"pr341-manual-corrections-v1","head":head,"comparison_contract":"primary-board-panel-map-v2","raw_pixel_score":{"status":"NOT_COMPARABLE","reason":"The approved boards contain composite and partial panels; this package preserves native reference/current/overlay/heatmap evidence but does not relabel resized-board differences as a fidelity percentage."},"truth_adjusted_pixel_score":{"status":"NOT_COMPARABLE","reason":"No structural masking was applied."},"states":[{"id":r["state"],"capture_stable":r["current_capture"].get("stable"),"capture_errors":r["current_capture"].get("errors",[]),"font_load":r["current_capture"].get("fontLoad",{}),"reference":r["reference_board"]} for r in records],"historical_measurements":{"reviewed_head":"a3a4228806a257c9e06f979129e4ba479387bcba","raw_visual_fidelity":62.151486,"label":"HISTORICAL_NON_COMPARABLE"}}
 (OUT/"score-report.json").write_text(json.dumps(score_report,indent=2)+"\n")
 provenance={"schema_version":"pr341-owner-review-provenance-v1","repository":"ronik18/earnalism-digital-library","pr_number":341,"pr_head":head,"capture_tool":{"playwright":"1.60.0","chromium":"148.0.7778.96","device_scale_factor":1},"source_changes_during_packaging":0,"production_mutations":0,"generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (OUT/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
 manifest={"schema_version":"earnalism-exact-primary-owner-review-v2","approved_copy":"Read the first 3 pages free. Listening requires an active Reading Pass.","head":head,"correction_contract_version":"pr341-manual-corrections-v1","corrections":CORRECTIONS,"states":records,"score_report":"score-report.json","status":"OWNER_REVIEWED_CORRECTIONS_APPROVAL_REQUIRED"}
 (OUT/"owner-review.json").write_text(json.dumps(manifest,indent=2)+"\n")
 panels="".join(f'<section><h2>{r["state"]}</h2><p>{r["product_truth_override"]}</p><table><tr><th>Region</th><td>{r["reference_board"]} {r["reference_crop"]}</td></tr><tr><th>Geometry</th><td>{r["current_capture"].get("geometry",[])}</td></tr></table><div><img src="{r["state"]}-reference.png"><img src="{r["state"]}-current.png"><img src="{r["state"]}-overlay.png"><img src="{r["state"]}-heatmap.png"></div></section>' for r in records)
 correction_html="".join("<li><strong>{}</strong> — {}</li>".format(key,value) for key,value in CORRECTIONS.items())
 (OUT/"owner-review.html").write_text(f'<!doctype html><meta charset="utf-8"><title>Earnalism reviewed corrections</title><style>body{{background:#f6f1e8;color:#142019;font:16px system-ui;margin:0}}header,section{{max-width:1600px;margin:auto;padding:20px}}section{{border-top:1px solid #c9a75b}}div{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}img{{width:100%;border:1px solid #c9a75b}}table{{font-size:12px;max-width:100%;overflow:auto}}@media(max-width:800px){{div{{grid-template-columns:repeat(2,1fr)}}}}</style><header><h1>Earnalism reviewed primary UI corrections</h1><p>Head: <code>{head}</code>. Review fixtures are local and sanitized; production access remains server-authoritative.</p><p>Raw heatmaps and overlays are visual evidence only. Their panel dimensions are not a comparable Pixelmatch denominator; see <code>score-report.json</code>.</p><ol>{correction_html}</ol></header>{panels}')
 pages[0].save(OUT/"owner-review.pdf",save_all=True,append_images=pages[1:])
 contact=Image.new("RGB",(1600,((len(records)+3)//4)*270),"#f6f1e8")
 for i,r in enumerate(records):
  image=Image.open(OUT/f'{r["state"]}-current.png').convert("RGB"); image.thumbnail((380,230)); x=(i%4)*400+10;y=(i//4)*270+25;contact.paste(image,(x,y));ImageDraw.Draw(contact).text((x,y-15),r["state"],fill="#142019",font=ImageFont.load_default())
 contact.save(OUT/"complete-contact-sheet.png")
 files=[]
 for file in sorted(OUT.iterdir()):
  if file.name in {"artifact.zip","manifest.json","manifest.sha256"}: continue
  files.append({"relative_path":file.name,"bytes":file.stat().st_size,"sha256":sha(file),"mime":mimetypes.guess_type(file.name)[0] or "application/octet-stream","source":"GENERATED_FROM_CURRENT_CAPTURE" if "current" in file.name or file.name in {"owner-review.html","owner-review.pdf","complete-contact-sheet.png","score-report.json","provenance.json"} else "ORIGINAL_ARTIFACT"})
 (OUT/"manifest.json").write_text(json.dumps({"head":head,"files":files},indent=2)+"\n")
 (OUT/"manifest.sha256").write_text(sha(OUT/"manifest.json")+"  manifest.json\n")
 with zipfile.ZipFile(OUT/"artifact.zip","w",zipfile.ZIP_DEFLATED) as archive:
  for file in OUT.iterdir():
   if file.name != "artifact.zip": archive.write(file,file.name)
 print(json.dumps({"states":len(records),"output":str(OUT),"artifact_sha256":sha(OUT/"artifact.zip")},indent=2))
if __name__=="__main__":main()
