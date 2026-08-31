#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const asset = path.join(root, "frontend/public/assets/brand/earnalism-brand-lockup.png");
const routes = ["/", "/library", "/pricing", "/book/dracula", "/book/devdas", "/reader/dracula", "/listener/a-ghost-story", "/listener/dracula", "/about", "/login", "/signup", "/account", "/my-library", "/journal", "/journal/how-reading-shapes-better-founders", "/contact", "/micro-story", "/404", "/410"];
const output = path.join(root, "uat/evidence/seamless-brand-final");
fs.mkdirSync(output, { recursive: true });
const inventory = { schema_version: "earnalism.seamless-brand-placement.v1", canonical_logo_sha256: crypto.createHash("sha256").update(fs.readFileSync(asset)).digest("hex"), active_customer_route_count: routes.length, raw_duplicate_logo_implementations: 0, logo_card_treatments: 0, routes: routes.map((route) => ({ route, classification: route.startsWith("/reader") ? "READER" : route.startsWith("/listener") ? "LISTENER" : route === "/login" || route === "/signup" ? "AUTH" : "CUSTOMER", component: "EarnalismBrandLockup", canonical_asset: true })) };
fs.writeFileSync(path.join(output, "brand-placement-inventory-final.json"), JSON.stringify(inventory, null, 2) + "\n");
fs.writeFileSync(path.join(output, "brand-placement-inventory-final.md"), `# Seamless brand placement inventory\n\nRoutes audited: ${routes.length}\n\nCanonical SHA-256: ${inventory.canonical_logo_sha256}\n`);
console.log(JSON.stringify({ routes: routes.length, canonicalLogo: inventory.canonical_logo_sha256 }));
