import test from "node:test";
import assert from "node:assert/strict";
import { openEditorialRoute } from "./lib/editorial_capture_readiness.mjs";
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
