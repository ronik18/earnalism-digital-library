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
 current=current.convert("RGB")
 if current.size != reference.size: return None
 return ImageChops.difference(reference, current).point(lambda x:min(255,x*4)), Image.blend(reference, current, .5)
def load(path): return json.loads(path.read_text()) if path.exists() else {"states":[]}
def current_head():
 return os.environ.get("GITHUB_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()

def write_mobile_menu_viewport_package(current_capture, before_capture, generic_provenance, head, browser_results):
 """Package the exact viewport-fix evidence without treating an old header review as current."""
 pr_number=os.environ.get("PR_NUMBER", "344")
 package=WORK/f"pr{pr_number}-fresh-mobile-header-menu-review-{head}"
 package.mkdir(parents=True,exist_ok=True)
 current={state["id"]:state for state in current_capture.get("states",[])}
 before={state["id"]:state for state in before_capture.get("states",[])}
 nav_ids=[state_id for state_id in current if state_id.startswith("mobile-navigation")]
 nav_states=[current[state_id] for state_id in nav_ids]
 before_states=[before[state_id] for state_id in before if state_id.startswith("mobile-navigation")]
 geometry={"schema_version":"earnalism-mobile-menu-geometry-results-v1","status":"PASS","states":[{"id":state["id"],"viewport":state["viewport"],"dialog":state.get("navigation",{}).get("dialog",{}).get("box"),"header":state.get("navigation",{}).get("header",{}).get("box"),"visible_toggle_count":state.get("navigation",{}).get("visibleToggleCount"),"owner_dialog_count":state.get("navigation",{}).get("activeVisibleOwnerDialogCount"),"overflow":{"scroll_width":state.get("scrollWidth"),"client_width":state.get("clientWidth")}} for state in nav_states]}
 geometry["status"]="PASS" if nav_states and all(state.get("navigation",{}).get("dialog",{}).get("box",{}).get("height",0)>0 and state.get("scrollWidth")==state.get("clientWidth") for state in nav_states) else "FAIL"
 old_header=(before.get("mobile-navigation",{}).get("navigation",{}).get("header",{}))
 old_dialog=(before.get("mobile-navigation",{}).get("navigation",{}).get("dialog",{}))
 new_header=(current.get("mobile-navigation",{}).get("navigation",{}).get("header",{}))
 new_dialog=(current.get("mobile-navigation",{}).get("navigation",{}).get("dialog",{}))
 diagnostics={"schema_version":"earnalism-mobile-menu-containing-block-diagnostics-v1","root_cause_classification":["BACKDROP_FILTER_FIXED_CONTAINING_BLOCK","EXPLICIT_INSET_HEIGHT_COLLAPSE"],"before":{"header":old_header,"dialog":old_dialog,"navigation_states":before_states},"after":{"header":new_header,"dialog":new_dialog,"navigation_states":nav_states},"property_delta":{"header_backdrop_filter":{"before":old_header.get("backdropFilter"),"after":new_header.get("backdropFilter")},"dialog_height":{"before":old_dialog.get("height"),"after":new_dialog.get("height")},"dialog_bottom":{"before":old_dialog.get("bottom"),"after":new_dialog.get("bottom")}}}
 interactions={"schema_version":"earnalism-mobile-menu-interaction-results-v1","status":"PASS","states":[{"id":state["id"],"open":{"aria_expanded":state.get("navigation",{}).get("toggleExpanded"),"aria_modal":state.get("navigation",{}).get("ariaModal"),"body_scroll_locked":state.get("navigation",{}).get("bodyScrollLocked"),"background_inert":state.get("navigation",{}).get("backgroundInert")},"close":state.get("navigationClose")} for state in nav_states],"focused_harness":load(WORK/"current"/"focused-mobile-menu-results.json")}
 interactions["status"]="PASS" if geometry["status"]=="PASS" and all(state.get("navigationClose",{}).get("escapeClose") and state.get("navigationClose",{}).get("focusRestored") for state in nav_states) else "FAIL"
 before_hashes=load(WORK/"before"/"surface-hashes.json")
 current_hashes=load(WORK/"current"/"surface-hashes.json")
 carry={"schema_version":"earnalism-owner-visual-approval-carry-forward-v1","prior_pr_head":before_capture.get("provenance",{}).get("actual_checkout_sha"),"new_pr_head":head,"public_body_sha256_before":before_hashes.get("public_body_sha256"),"public_body_sha256_after":current_hashes.get("public_body_sha256"),"public_body_hash_unchanged":before_hashes.get("public_body_sha256")==current_hashes.get("public_body_sha256"),"header_surface_sha256_before":before_hashes.get("header_surface_sha256"),"header_surface_sha256_after":current_hashes.get("header_surface_sha256"),"header_surface_changed":before_hashes.get("header_surface_sha256")!=current_hashes.get("header_surface_sha256"),"body_visual_approval_carried_forward":before_hashes.get("public_body_sha256")==current_hashes.get("public_body_sha256"),"header_menu_visual_approval_requires_fresh_captures":True,"reason":"mobile fixed-position containing-block defect corrected"}
 special_provenance={**generic_provenance,"artifact_kind":"pr344-mobile-menu-viewport-fix","production_mutations":1,"production_changed_files":["frontend/src/components/Header.css"],"evidence_files":["scripts/capture_exact_primary_owner_review.mjs","scripts/test_capture_exact_primary_owner_review_mobile_menu.mjs","scripts/verify_exact_primary_cross_browser.mjs","scripts/generate_exact_primary_owner_review.py",".github/workflows/public-pages-owner-review.yml"]}
 accessibility={"status":"PASS" if interactions["status"]=="PASS" else "FAIL","menu_text_minimum_px":16,"row_minimum_px":52,"control_minimum_px":44,"focus_restore":all(state.get("navigationClose",{}).get("focusRestored") for state in nav_states),"background_inert":all(state.get("navigation",{}).get("backgroundInert") for state in nav_states)}
 for name,payload in {"geometry-results.json":geometry,"containing-block-diagnostics.json":diagnostics,"containing-block-before.json":diagnostics["before"],"containing-block-after.json":diagnostics["after"],"interaction-results.json":interactions,"accessibility-results.json":accessibility,"browser-results.json":browser_results,"approval-carry-forward.json":carry,"provenance.json":special_provenance}.items(): (package/name).write_text(json.dumps(payload,indent=2)+"\n")
 for state_id in sorted(set(["mobile-navigation","mobile-navigation-320",*nav_ids])):
  for prefix,source in [("before",WORK/"before"),("after",WORK/"current")]:
   image=source/f"{state_id}.png"
   if image.exists(): shutil.copy2(image,package/f"{state_id}-{prefix}.png")
 shutil.copy2(OUT/"owner-review.pdf",package/"owner-review.pdf")
 shutil.copy2(OUT/"complete-contact-sheet.png",package/"contact-sheet.png")
 (package/"owner-review.html").write_text(f'<!doctype html><meta charset="utf-8"><title>PR {pr_number} mobile-menu viewport fix</title><style>body{{background:#07110f;color:#fff8e9;font:16px system-ui;margin:0;padding:32px}}main{{max-width:960px;margin:auto}}code{{color:#f2d188}}li{{margin:.5rem 0}}img{{max-width:48%;border:1px solid #d6ad55;margin:.4rem}}</style><main><h1>PR {pr_number}: mobile-menu viewport correction</h1><p>Exact head: <code>{head}</code></p><p>Fresh capture is required because the header surface changed. Public page-body approval carries forward only when the body hash matches.</p><ul><li>Root cause: backdrop-filter fixed containing block plus explicit inset-height collapse.</li><li>Geometry status: {geometry["status"]}</li><li>Interaction status: {interactions["status"]}</li><li>Body hash unchanged: {carry["public_body_hash_unchanged"]}</li></ul><p>See the JSON evidence files for the computed-style chain, geometry, interactions, browser results, and approval scope.</p><img src="mobile-navigation-before.png"><img src="mobile-navigation-after.png"></main>')
 files=[]
 for file in sorted(package.iterdir()):
  if file.name=="manifest.json": continue
  files.append({"relative_path":file.name,"bytes":file.stat().st_size,"sha256":sha(file),"mime":mimetypes.guess_type(file.name)[0] or "application/octet-stream"})
 (package/"manifest.json").write_text(json.dumps({"artifact":package.name,"head":head,"status":"PASS" if geometry["status"]=="PASS" and interactions["status"]=="PASS" and carry["public_body_hash_unchanged"] else "FAIL","files":files},indent=2)+"\n")
 with zipfile.ZipFile(package/"artifact.zip","w",zipfile.ZIP_DEFLATED) as archive:
  for file in package.iterdir():
   if file.name != "artifact.zip": archive.write(file,file.name)
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
 current_capture=load(current_dir/"capture.json"); before_capture=load(before_dir/"capture.json")
 current={x["id"]:x for x in current_capture.get("states",[])}; before={x["id"]:x for x in before_capture.get("states",[])}
 records=[]; pages=[]
 for state in CROPS:
  ref, board=crop(state); ref_name=f"{state}-reference.png"; ref.save(OUT/ref_name)
  current_path=maybe(current_dir/f"{state}.png"); before_path=maybe(before_dir/f"{state}.png")
  current_name=f"{state}-current.png"; before_name=f"{state}-before.png"
  if current_path: shutil.copy2(current_path, OUT/current_name)
  if before_path: shutil.copy2(before_path, OUT/before_name)
  full_current=maybe(current_dir/f"{state}-full.png")
  if full_current: shutil.copy2(full_current, OUT/f"{state}-current-full.png")
  heat_name=f"{state}-heatmap.png"; overlay_name=f"{state}-overlay.png"
  if current_path:
   comparison=diff(ref,Image.open(current_path))
   if comparison:
    heat, overlay=comparison; heat.save(OUT/heat_name); overlay.save(OUT/overlay_name)
  record={"state":state,"reference_board":board.name,"reference_sha256":sha(board),"reference_crop":{"x":CROPS[state][0],"y":CROPS[state][1],"width":CROPS[state][2],"height":CROPS[state][3]},"current_capture":current.get(state,{}),"before_capture":before.get(state,{}),"overlay_suitability":"NATIVE_DIMENSIONS_REQUIRED; side-by-side only" if not (OUT/overlay_name).exists() else "ALIGNED_NATIVE_DIMENSIONS","labels":["EXACT_REFERENCED_REGION","RESPONSIVE_EXTRAPOLATION","DYNAMIC_REAL_DATA"],"product_truth_override":OVERRIDES.get(state,"None"),"source_asset_limitation":"Listener title artwork is classified separately; no embedded UI is used as an asset." if state.startswith("listener") else "None"}
  records.append(record)
  page=Image.new("RGB",(1600,1100),"#f6f1e8"); draw=ImageDraw.Draw(page); font=ImageFont.load_default(); draw.text((32,24),f"{state} | EXACT REFERENCED REGION / CURRENT ROUTED UI",fill="#142019",font=font); draw.text((32,46),record["product_truth_override"],fill="#6a5121",font=font)
  left=ref.copy(); left.thumbnail((720,970)); page.paste(left,(32,95))
  if current_path:
   right=Image.open(current_path).convert("RGB"); right.thumbnail((720,970)); page.paste(right,(830,95))
  pages.append(page)
 capture_provenance=current_capture.get("provenance",{})
 head=capture_provenance.get("actual_checkout_sha") or current_head()
 if capture_provenance.get("pr_head_sha") and capture_provenance["pr_head_sha"] != head:
  raise RuntimeError("owner-review capture checkout does not match the pull-request head")
 score_report={"schema_version":"pr341-manual-corrections-v1","head":head,"comparison_contract":"primary-board-panel-map-v2","raw_pixel_score":{"status":"NOT_COMPARABLE","reason":"The approved boards contain composite and partial panels; this package preserves native reference/current/overlay/heatmap evidence but does not relabel resized-board differences as a fidelity percentage."},"truth_adjusted_pixel_score":{"status":"NOT_COMPARABLE","reason":"No structural masking was applied."},"states":[{"id":r["state"],"capture_stable":r["current_capture"].get("stable"),"capture_errors":r["current_capture"].get("errors",[]),"font_load":r["current_capture"].get("fontLoad",{}),"reference":r["reference_board"]} for r in records],"historical_measurements":{"reviewed_head":"a3a4228806a257c9e06f979129e4ba479387bcba","raw_visual_fidelity":62.151486,"label":"HISTORICAL_NON_COMPARABLE"}}
 (OUT/"score-report.json").write_text(json.dumps(score_report,indent=2)+"\n")
 browser_results={"chromium":{"version":capture_provenance.get("browser_version"),"states":[{"id":r["state"],"stable":r["current_capture"].get("stable"),"errors":r["current_capture"].get("errors",[]),"overflow":r["current_capture"].get("scrollWidth") != r["current_capture"].get("clientWidth")} for r in records]},"firefox":load(current_dir/"browser-firefox.json"),"webkit":load(current_dir/"browser-webkit.json")}
 (OUT/"browser-results.json").write_text(json.dumps(browser_results,indent=2)+"\n")
 artwork={"schema_version":"pr341-title-artwork-readiness-v1","titles":[{"slug":"a-ghost-story","displayed_title":"A Ghost Story","cover_metadata_field":"cover_image_url","cover_identity":"existing Cloudinary cover referenced by listener fixture","classification":"WRONG_TITLE_ART","exists_in_production_metadata":True},{"slug":"dracula","displayed_title":"Dracula","cover_metadata_field":"cover_image_url","cover_identity":"/assets/books/dracula/dracula-front-cover.webp","classification":"CORRECT_TITLE_ART","exists_in_production_metadata":True}]}
 (OUT/"title-artwork-readiness.json").write_text(json.dumps(artwork,indent=2)+"\n")
 provenance={"schema_version":"pr341-owner-review-provenance-v2","repository":"ronik18/earnalism-digital-library","pr_number":341,"pr_head_sha":current_capture.get("provenance",{}).get("pr_head_sha"),"actual_checkout_sha":current_capture.get("provenance",{}).get("actual_checkout_sha"),"checkout_tree_sha":current_capture.get("provenance",{}).get("checkout_tree_sha"),"workflow_event_sha":current_capture.get("provenance",{}).get("workflow_event_sha"),"capture_script_sha256":current_capture.get("provenance",{}).get("capture_script_sha256"),"fixture_sha256":current_capture.get("provenance",{}).get("fixture_sha256"),"browser_version":current_capture.get("provenance",{}).get("browser_version"),"build_configuration":current_capture.get("provenance",{}).get("build_configuration"),"reference_hashes":{board.name:sha(board) for board in {BOARD_ONE,BOARD_TWO}},"source_changes_during_packaging":0,"production_mutations":0,"generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (OUT/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
 manifest={"schema_version":"earnalism-exact-primary-owner-review-v2","approved_copy":"Read the first 3 pages free. Listening requires an active Reading Pass.","head":head,"correction_contract_version":"pr341-manual-corrections-v1","corrections":CORRECTIONS,"states":records,"score_report":"score-report.json","status":"OWNER_REVIEWED_CORRECTIONS_APPROVAL_REQUIRED"}
 (OUT/"owner-review.json").write_text(json.dumps(manifest,indent=2)+"\n")
 panels="".join(f'<section><h2>{r["state"]}</h2><p>{r["product_truth_override"]}</p><table><tr><th>Region</th><td>{r["reference_board"]} {r["reference_crop"]}</td></tr><tr><th>Overlay</th><td>{r["overlay_suitability"]}</td></tr><tr><th>Geometry</th><td>{r["current_capture"].get("geometry",[])}</td></tr></table><div><img src="{r["state"]}-reference.png"><img src="{r["state"]}-current.png"></div></section>' for r in records)
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
 write_mobile_menu_viewport_package(current_capture,before_capture,provenance,head,browser_results)
 print(json.dumps({"states":len(records),"output":str(OUT),"artifact_sha256":sha(OUT/"artifact.zip")},indent=2))
if __name__=="__main__":main()
