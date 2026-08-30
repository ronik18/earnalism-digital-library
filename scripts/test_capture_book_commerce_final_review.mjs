#!/usr/bin/env node
import fs from "node:fs"; import path from "node:path";
const script=fs.readFileSync(new URL("./capture_book_commerce_final_review.mjs",import.meta.url),"utf8");
const required=["book-about-desktop-1440","book-chapters-desktop","book-chapters-mobile","book-secondary-desktop","commerce-1024","commerce-768","commerce-430","commerce-320","book-interaction-results.json","commerce-geometry-results.json"];
const absent=required.filter((id)=>!script.includes(id)); if(absent.length) throw new Error(`Required harness evidence absent: ${absent.join(", ")}`);
const out=process.env.BOOK_COMMERCE_TEST_OUTPUT; if(out){ for(const file of ["capture-results.json","book-interaction-results.json","fixture-offer-results.json","commerce-geometry-results.json","heading-results.json","book-content-capability-results.json","live-offer-results.json","book-commerce-browser-results.json"]){if(!fs.existsSync(path.join(out,file)))throw new Error(`Required result missing: ${file}`); const body=fs.readFileSync(path.join(out,file),"utf8"); if(/PENDING|NOT RUN|WORKFLOW RUNNING/.test(body))throw new Error(`Non-final evidence in ${file}`);} }
console.log(JSON.stringify({status:"PASS",required_states:required.length}));
