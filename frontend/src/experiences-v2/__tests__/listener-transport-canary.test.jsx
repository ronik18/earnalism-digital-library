import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";
const book = () => ({ slug: "the-open-window", title: "The Open Window", author: "Saki", audio_enabled: false, audiobook_enabled: false, _readerManifest: { access: {authenticated:true,role:"user"}, audio: {enabled:false,assets:{},transport_canary:{enabled:true,slug:"the-open-window",scope:"transport_canary_only_no_customer_discovery",rollout_percentage:5,package_version:`sha256-${"a".repeat(64)}`,release_descriptor_sha256:"b".repeat(64),duration_ms:491436}}}});
test("authenticated selected transport canary renders without public approval or provider URLs",()=>{
 const value=book();const result=listenerReleasePresentation(value);
 expect(result.chapterLabel).toBe("Full audiobook");expect(result.canRender).toBe(true);expect(result.release.status).toBe("transport_canary");expect(result.mediaUrl).toBe("");expect(result.packageManifestUrl).toBe("");expect(value.audio_enabled).toBe(false);
});
test.each(["guest","wrong_slug","wrong_scope","bad_version","wrong_percentage","not_selected"])("%s remains denied",(kind)=>{
 const value=book();const canary=value._readerManifest.audio.transport_canary;
 if(kind==="guest")value._readerManifest.access.authenticated=false;
 if(kind==="wrong_slug")canary.slug="other";
 if(kind==="wrong_scope")canary.scope="public";
 if(kind==="bad_version")canary.package_version="bad";
 if(kind==="wrong_percentage")canary.rollout_percentage=100;
 if(kind==="not_selected")canary.enabled=false;
 expect(listenerReleasePresentation(value).canRender).toBe(false);
});
