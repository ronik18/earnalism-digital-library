import React, { act } from "react";
import { createRoot } from "react-dom/client";
import AudiobookMusicNotice from "./AudiobookMusicNotice";
import { approvedAudiobookMusicCredit } from "../lib/audiobookMusicCredits";
import credits from "../lib/audiobookMusicCredits.json";
const descriptor = Object.keys(credits)[0];
const approved = {slug: "the-selfish-giant",audio_enabled:true,audiobook_enabled:true,audiobook_release_gate:"APPROVED",audio_qa_status:"QA_PASSED",audiobook_delivery_mode:"PROTECTED_PACKAGE_V2",audiobook_package_version:`sha256-${"1".repeat(64)}`,audiobook_release_descriptor_sha256:descriptor};
beforeAll(()=>{global.IS_REACT_ACT_ENVIRONMENT=true;});
test("renders creator, source, licence, modifications and component scope only for exact release",async()=>{
 const node=document.createElement("div");const root=createRoot(node);
 await act(async()=>root.render(<AudiobookMusicNotice book={approved}/>));
 expect(node.textContent).toContain("Kevin MacLeod");expect(node.textContent).toContain("Heartbreaking");expect(node.textContent).toContain("Changes:");expect(node.textContent).toContain("no restrictions");expect(node.textContent).toContain("separate narration");
 expect(node.querySelector('a[rel="license"]').href).toBe("https://creativecommons.org/licenses/by/4.0/");
 expect(node.querySelector('a').href).toContain("isrc=USUAN1100208");await act(async()=>root.unmount());
});
test.each([{}, {...approved,audiobook_release_descriptor_sha256:"b5b378168211d61ac80341e74cbfacaf0d5590a18300a5c91db4684626e343a2"}, {...approved,slug:"the-open-window"}, {...approved,audio_enabled:false}, {...approved,audiobook_release_gate:"PENDING"}, {...approved,audiobook_package_version:"invalid"}])("old, disabled or unrelated release gets no music claim",book=>expect(approvedAudiobookMusicCredit(book)).toBeNull());
