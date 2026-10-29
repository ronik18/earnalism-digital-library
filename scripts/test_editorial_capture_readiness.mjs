import test from "node:test";
import assert from "node:assert/strict";
import { openEditorialRoute, prepareEditorialScreenshot } from "./lib/editorial_capture_readiness.mjs";
function fixture(failingStage) {
  const stages=[];
  const page={
    async goto(url,options) { stages.push("document"); assert.equal(options.waitUntil,"domcontentloaded"); if(failingStage==="document")throw Error("document failed"); return {status:()=>200}; },
    async waitForSelector(selector,options) { const stage=selector.includes("site-header")?"hydration":"route";stages.push(stage);assert.equal(options.state,"visible");if(failingStage===stage)throw Error(stage+" failed"); },
    async evaluate(callback,route) { stages.push("navigation");assert.equal(route,"/journal"); },
    async waitForFunction(callback,arg,options) { stages.push("assets");assert.equal(options.timeout,30000);if(failingStage==="assets")throw Error("assets failed"); },
  };
  return {page,stages};
}
test("ongoing unrelated connections do not gate a rendered editorial route",async()=>{
  const {page,stages}=fixture();const response=await openEditorialRoute(page,"http://127.0.0.1:13130","/journal","[data-testid=journal-page]");
  assert.equal(response.status(),200);assert.deepEqual(stages,["document","hydration","navigation","route","assets"]);
});
for(const stage of ["document","hydration","route","assets"])test("missing "+stage+" remains fatal without retry",async()=>{
  const {page,stages}=fixture(stage);await assert.rejects(openEditorialRoute(page,"http://127.0.0.1:13130","/journal","[data-testid=journal-page]"),new RegExp(stage+" failed"));assert.equal(stages.filter(s=>s===stage).length,1);
});

for (const failure of [null, "foreground", "layout", "frame"]) test("one bounded screenshot preparation: " + (failure || "ready"), async () => {
  const stages = [];
  const page = {
    async bringToFront() { stages.push("foreground"); if (failure === "foreground") throw Error(failure); },
    async waitForFunction(fn, arg, options) { stages.push("layout"); assert.equal(options.timeout, 10000); if (failure === "layout") throw Error(failure); },
    async evaluate(fn) { stages.push("frame"); assert.match(String(fn), /requestAnimationFrame/); assert.match(String(fn), /3000/); if (failure === "frame") throw Error(failure); },
  };
  if (failure) await assert.rejects(prepareEditorialScreenshot(page), new RegExp(failure));
  else await prepareEditorialScreenshot(page);
  assert.equal(new Set(stages).size, stages.length);
  if (!failure) assert.deepEqual(stages, ["foreground", "layout", "frame"]);
});
