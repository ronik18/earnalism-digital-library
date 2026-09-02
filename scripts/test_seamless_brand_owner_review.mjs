#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
const expected=["home-desktop","home-mobile","home-mobile-zoom-200","reader-mobile-390","reader-mobile-320","listener-mobile-390","listener-mobile-320","account-mobile","library-footer-mobile"];
const temp=fs.mkdtempSync(path.join(os.tmpdir(),"seamless-brand-test-")); const png=path.join(temp,"x.png"); fs.writeFileSync(png,Buffer.from("89504e470d0a1a0a","hex"));
const valid={states:expected.map((id)=>({id,screenshot:"x.png",screenshotSha256:crypto.createHash("sha256").update(fs.readFileSync(png)).digest("hex")}))};
function check(data){assert.equal(data.states.length,9);assert.deepEqual(new Set(data.states.map(s=>s.id)),new Set(expected));for(const s of data.states){assert.ok(s.screenshot);assert.ok(s.screenshotSha256)}}
check(valid); for(const missing of expected){const copy=structuredClone(valid);copy.states=copy.states.filter(s=>s.id!==missing);assert.throws(()=>check(copy));} const dup=structuredClone(valid);dup.states.push(dup.states[0]);assert.throws(()=>check(dup)); console.log(JSON.stringify({result:"PASS",negativeCases:10,positiveCases:1}));
