import { readFileSync } from 'node:fs';
import { BRAND_DATA_URI } from './brand-asset.mjs';
export const schema = JSON.parse(readFileSync(new URL('./receipt.schema.v1.json', import.meta.url)));
export const GST_STATEMENT = 'Reo Enterprise is not registered under GST. No GST has been charged or collected. This document is a payment receipt, not a GST tax invoice.';
export const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// This deliberately small validator implements only the keywords used by this
// bundled schema. Unknown keywords must be added here before changing the schema.
export function validate(data) {
  function check(v, rule, path) {
    const fail = () => { throw new TypeError(`Invalid receipt data at ${path}`); };
    if ('const' in rule && v !== rule.const) fail();
    if (rule.enum && !rule.enum.includes(v)) fail();
    if (rule.type === 'object') {
      if (!v || typeof v !== 'object' || Array.isArray(v)) fail();
      for (const k of rule.required) if (!Object.hasOwn(v,k)) fail();
      for (const k of Object.keys(v)) {
        if (!Object.hasOwn(rule.properties,k)) fail();
        check(v[k],rule.properties[k],`${path}.${k}`);
      }
    }
    if (rule.type === 'integer' && !Number.isSafeInteger(v)) fail();
    if (rule.type === 'string') {
      if (typeof v !== 'string' || !v.trim() || [...v].length < rule.minLength || [...v].length > rule.maxLength) fail();
      if (rule.pattern && !new RegExp(rule.pattern,'u').test(v)) fail();
      // Reject bidi overrides and invisible control characters in all display fields.
      if (/[\u202A-\u202E\u2066-\u2069\u200B-\u200F\uFEFF]/u.test(v)) fail();
      if (rule.format === 'email' && !/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(v)) fail();
      if (rule.format === 'date-time' && (!Number.isFinite(Date.parse(v)) || new Date(v).toISOString() !== v.replace('Z','.000Z'))) fail();
    }
  }
  check(data,schema,'$');
  if (Date.parse(data.issuedAtUtc) < Date.parse(data.capturedAtUtc)) throw new TypeError('Issue timestamp precedes capture');
  return structuredClone(data);
}
export function formatINR(paise) {
  if (!Number.isSafeInteger(paise) || paise < 0) throw new TypeError('Integer paise required');
  return `₹${Math.floor(paise/100)}.${String(paise%100).padStart(2,'0')}`;
}
export function formatIST(utc) {
  const parts = new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(utc));
  const p = Object.fromEntries(parts.map(x=>[x.type,x.value]));
  return `${p.day} ${p.month} ${p.year}, ${p.hour}:${p.minute} IST`;
}
const e = escapeHTML;
function time(utc) { return `<time datetime="${e(utc)}">${e(formatIST(utc))}</time>`; }
const css = readFileSync(new URL('./receipt.css',import.meta.url),'utf8');
export function renderReceipt(input) {
  const d=validate(input), seller=d.sellerSnapshot, buyer=d.buyerSnapshot, product=d.productSnapshot;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SAMPLE Payment receipt | Earnalism</title><style>${css}</style></head><body><main class="receipt ${buyer.name.length > 40 || buyer.email.length > 60 || d.capturedPaymentReference.length > 40 ? 'long-content' : ''}" aria-labelledby="receipt-title">
  <header class="brand"><img src="${BRAND_DATA_URI}" width="640" height="192" alt="Earnalism - Where Learning Becomes Earning. A Reo Enterprise venture."><span class="sample">SAMPLE<br><small>Design specimen</small></span></header>
  <section class="intro"><p class="eyebrow">THE EARNALISM DIGITAL LIBRARY</p><h1 id="receipt-title">Payment receipt</h1><p class="lead">A little time for timeless reading.</p></section>
  <section class="summary" aria-label="Receipt summary"><div><p class="label">Receipt number</p><p class="reference">${e(d.receiptNumber)}</p><p class="issued">Issued ${time(d.issuedAtUtc)}</p></div><div class="paid"><span class="label">Amount received · ${e(d.amounts.currency)}</span><strong>${formatINR(d.amounts.paidAmountPaise)}</strong><span class="status">Payment ${e(d.paymentStatus.toLowerCase())}</span></div></section>
  <section class="parties" aria-label="Seller and buyer"><div><h2>Received from</h2><p class="person">${e(buyer.name)}</p><p class="wrap">${e(buyer.email)}</p></div><div><h2>Received by</h2><p class="person">${e(seller.legalName)}</p><address>${e(seller.address)}</address></div></section>
  <section class="purchase" aria-label="Purchase details"><h2 class="sr-only">Purchase</h2><table><caption class="sr-only">Reading Pass payment details, in Indian rupees</caption><thead><tr><th scope="col">Description</th><th scope="col">Qty</th><th scope="col">Amount</th></tr></thead><tbody><tr><th scope="row">${e(product.name)}<span class="duration">${product.durationSeconds / 60} minutes / ${product.durationSeconds} seconds</span></th><td>${product.quantity}</td><td>${formatINR(product.unitAmountPaise)}</td></tr></tbody><tfoot><tr><th scope="row" colspan="2">Total paid</th><td>${formatINR(d.amounts.paidAmountPaise)}</td></tr></tfoot></table></section>
  <section class="record" aria-labelledby="record-title"><h2 id="record-title">Payment record</h2><dl><div><dt>Order number</dt><dd>${e(d.orderNumber)}</dd></div><div><dt>Captured payment reference</dt><dd>${e(d.capturedPaymentReference)}</dd></div><div><dt>Payment captured</dt><dd>${time(d.capturedAtUtc)}</dd></div><div><dt>Pass entitlement status</dt><dd>${e(d.entitlementStatus)}</dd></div></dl></section>
  <aside class="notice" aria-label="GST registration statement"><p>${GST_STATEMENT}</p></aside>
  <footer><p>Thank you for choosing Earnalism.</p><p><a href="mailto:${e(seller.supportEmail)}">${e(seller.supportEmail)}</a><span aria-hidden="true"> · </span><a href="${e(seller.website)}">theearnalism.com</a></p><small>SAMPLE · Synthetic data · Not an issued receipt</small></footer>
  </main></body></html>`;
}

export function renderEmail(input,{inlineLogo=false}={}) {
 const d=validate(input), s=d.sellerSnapshot;
 const row=(k,v)=>`<tr><th scope="row" style="text-align:left;padding:9px 8px 9px 0;font-weight:normal;vertical-align:top">${e(k)}</th><td style="padding:9px 0;overflow-wrap:anywhere">${v}</td></tr>`;
 return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SAMPLE Earnalism payment receipt</title></head><body style="margin:0;background:#F0E4D5;color:#35292B;font:15px/1.65 Arial,sans-serif"><div style="display:none;max-height:0;overflow:hidden">SAMPLE: ${formatINR(d.amounts.paidAmountPaise)} received for your Earnalism Reading Pass.</div><main style="max-width:560px;margin:24px auto;background:#FFFAF3;border-top:5px solid #521D32;padding:28px 24px"><header><img src="${inlineLogo?BRAND_DATA_URI:'cid:earnalism-logo'}" alt="Earnalism - Where Learning Becomes Earning. A Reo Enterprise venture." width="260" style="display:block;max-width:100%;height:auto"><p style="color:#521D32;font-size:12px;letter-spacing:2px">SAMPLE · DESIGN SPECIMEN</p></header><h1 style="font:32px/1.2 Georgia,serif;color:#521D32;margin:30px 0 16px">Payment received</h1><p>Hello ${e(d.buyerSnapshot.name)},</p><p>Thank you for choosing Earnalism. Your payment of <strong>${formatINR(d.amounts.paidAmountPaise)}</strong> for ${e(d.productSnapshot.name)} (${d.productSnapshot.durationSeconds/60} minutes / ${d.productSnapshot.durationSeconds} seconds) is recorded as <strong>${e(d.paymentStatus)}</strong>.</p><table style="width:100%;border-collapse:collapse;font-size:13px;border-top:1px solid #D6BC95;border-bottom:1px solid #D6BC95"><caption style="text-align:left;font-weight:bold;padding:12px 0;color:#3E1727">Your payment details</caption><tbody>${row('Receipt number',e(d.receiptNumber))}${row('Order number',e(d.orderNumber))}${row('Capture reference',e(d.capturedPaymentReference))}${row('Captured',time(d.capturedAtUtc))}${row('Issued',time(d.issuedAtUtc))}${row('Entitlement',e(d.entitlementStatus))}</tbody></table><p>Your PDF payment receipt is attached.</p><p style="padding:14px;background:#F0E4D5;font-size:12px">${GST_STATEMENT}</p><footer style="font-size:12px"><p><strong>${e(s.legalName)}</strong><br>${e(s.address)}</p><p>Need help? <a style="color:#521D32" href="mailto:${e(s.supportEmail)}">${e(s.supportEmail)}</a><br><a style="color:#521D32" href="${e(s.website)}">theearnalism.com</a></p><p>SAMPLE · Synthetic data · Not an issued receipt</p></footer></main></body></html>`;
}
export function emailText(input) {
 const d=validate(input);
 return `SAMPLE - Synthetic data - Not an issued receipt\nHello ${d.buyerSnapshot.name},\nPayment received: ${formatINR(d.amounts.paidAmountPaise)} INR\n${d.productSnapshot.name}: ${d.productSnapshot.durationSeconds/60} minutes / ${d.productSnapshot.durationSeconds} seconds\nReceipt: ${d.receiptNumber}\nOrder: ${d.orderNumber}\nCapture reference: ${d.capturedPaymentReference}\nCaptured: ${formatIST(d.capturedAtUtc)}\nIssued: ${formatIST(d.issuedAtUtc)}\nPayment: ${d.paymentStatus}\nEntitlement: ${d.entitlementStatus}\nYour PDF payment receipt is attached.\n${GST_STATEMENT}\n${d.sellerSnapshot.legalName}\n${d.sellerSnapshot.address}\n${d.sellerSnapshot.supportEmail}\n${d.sellerSnapshot.website}\n`;
}
