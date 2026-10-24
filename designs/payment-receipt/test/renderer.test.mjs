import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {validate,renderReceipt,renderEmail,escapeHTML,formatINR,formatIST,GST_STATEMENT,emailText} from '../renderer.mjs';
import {makeEmailFixture} from '../email-fixture.mjs';
const sample=JSON.parse(readFileSync(new URL('../sample.v1.json',import.meta.url)));
const change=fn=>{const d=structuredClone(sample);fn(d);return d;};
test('sample renders exact amounts, identifiers, UTC and IST',()=>{
 const html=renderReceipt(sample);
 for(const text of ['₹49.00',sample.receiptNumber,sample.orderNumber,sample.capturedPaymentReference,'24 Oct 2026, 18:00 IST',sample.capturedAtUtc,'30 minutes / 1800 seconds',GST_STATEMENT,'SAMPLE','PENDING'])assert.ok(html.includes(text),text);
 assert.equal(formatINR(4900),'₹49.00'); assert.equal(formatIST('2026-10-24T20:00:00Z'),'25 Oct 2026, 01:30 IST');
});
test('missing, unknown, unsafe and disabled financial states fail closed',()=>{
 for(const fn of [d=>delete d.receiptNumber,d=>d.gstStatus='REGISTERED',d=>d.paymentStatus='AUTHORIZED',d=>d.entitlementStatus='GUESS',d=>d.templateVersion='tax-v2',d=>d.sample="false",d=>delete d.sample,d=>d.amounts.paidAmountPaise=49,d=>d.amounts.paidAmountPaise=4900.1,d=>d.amounts.currency='USD',d=>d.tax=0,d=>d.buyerSnapshot.rawHtml='<b>x</b>',d=>d.capturedAtUtc='2026-02-30T12:00:00Z',d=>d.issuedAtUtc='2026-10-23T12:00:00Z',d=>d.capturedAtUtc='2026-10-24T12:30:00+00:00',d=>d.buyerSnapshot.name='x\u202ey',d=>d.buyerSnapshot.name='a'.repeat(71)])assert.throws(()=>renderReceipt(change(fn)));
});
test('all untrusted strings escape in both HTML contexts',()=>{
 const payload=`<img src=x onerror="alert(1)"> & 'test'`;
 const d=change(d=>{d.buyerSnapshot.name=payload;d.capturedPaymentReference=payload;});
 for(const html of [renderReceipt(d),renderEmail(d)]){assert.ok(!html.includes('<img src=x'));assert.ok(html.includes(escapeHTML(payload)));assert.ok(!html.includes('<script'));}
 assert.equal(escapeHTML('&<>"\''),'&amp;&lt;&gt;&quot;&#39;');
});
test('entitlement is independent of captured payment; never inferred',()=>{
 for(const status of ['PENDING','ACTIVE','EXPIRED','REVOKED']){
 const d=change(d=>d.entitlementStatus=status);assert.ok(renderReceipt(d).includes(`>${status}</dd>`));assert.ok(renderEmail(d).includes(`>${status}</td>`));}
});
test('semantic, self contained receipt and lightweight email',()=>{
 const html=renderReceipt(sample),email=renderEmail(sample);
 for(const tag of ['<main','<header','<h1','<table','scope="col"','scope="row"','<caption','<address','<time datetime=','lang="en"'])assert.ok(html.includes(tag));
 assert.ok(html.includes('data:image/png;base64,'));assert.ok(email.includes('cid:earnalism-logo'));assert.ok(!email.includes('<style>'));assert.ok(!html.includes('src="http'));assert.ok(!/\bGSTIN\b|\bSAC\b|GST\s*0|\bexempt\b/i.test(html.replace(/data:image\/png;base64,[^"]+/g,'')));
});
test('validated snapshot is cloned and caller remains unchanged',()=>{
 const copy=JSON.stringify(sample),model=validate(sample);model.buyerSnapshot.name='Changed';renderReceipt(sample);assert.equal(JSON.stringify(sample),copy);
});
test('boolean sample controls every marking; false is tested only with synthetic data',()=>{
 const d=change(d=>{d.sample=false;d.capturedPaymentReference='OFFLINE-FIXTURE-000001';});
 for(const output of [renderReceipt(d),renderEmail(d),emailText(d)]) assert.ok(!output.includes('SAMPLE'));
 for(const output of [renderReceipt(sample),renderEmail(sample),emailText(sample)]) assert.ok(output.includes('SAMPLE'));
 assert.equal(validate(d).sample,false);
});
test('absent and partial buyer identity render without inventing identity',()=>{
 for(const fn of [d=>delete d.buyerSnapshot,d=>d.buyerSnapshot={},d=>delete d.buyerSnapshot.name,d=>delete d.buyerSnapshot.email]){
  const d=change(fn),receipt=renderReceipt(d),email=renderEmail(d),text=emailText(d);
  for(const output of [receipt,email,text]){assert.ok(!output.includes('undefined'));assert.ok(!output.includes('null'));}
  if(!d.buyerSnapshot?.name&&!d.buyerSnapshot?.email)assert.ok(receipt.includes('Buyer details not supplied.'));
  if(!d.buyerSnapshot?.name){assert.ok(email.includes('<p>Hello,</p>'));assert.ok(text.includes('\nHello,\n'));assert.ok(!receipt.includes('Sample Reader'));}
  if(!d.buyerSnapshot?.email)assert.ok(!receipt.includes('reader@example.invalid'));
 }
 for(const invalid of [null,{name:''},{email:''},{email:'invalid'},{name:17}])assert.throws(()=>validate(change(d=>d.buyerSnapshot=invalid)));
});
test('valid leap date and UTC midnight rollover are accepted in both modes',()=>{
 for(const sampleFlag of [true,false]){
  const d=change(d=>{d.sample=sampleFlag;d.capturedAtUtc='2028-02-29T23:59:59Z';d.issuedAtUtc='2028-03-01T00:00:00Z';});
  assert.ok(renderReceipt(d).includes('01 Mar 2028, 05:29 IST'));assert.ok(renderEmail(d).includes('01 Mar 2028, 05:30 IST'));
 }
});
test('rendered PDF fixture attaches exact bytes and CID logo',()=>{
 const path=new URL('../output/receipt.pdf',import.meta.url);assert.ok(existsSync(path),'Render the HTML PDF before running focused tests');
 const pdf=readFileSync(path),fixture=makeEmailFixture(sample,pdf);
 const match=fixture.raw.match(/Content-Type: application\/pdf\r\nContent-Transfer-Encoding: base64\r\nContent-Disposition: attachment;[^\r]+\r\n\r\n([A-Za-z0-9+/=\r\n]+?)--earnalism-mixed-v1--/);
 assert.ok(match);assert.deepEqual(Buffer.from(match[1],'base64'),pdf);assert.equal(fixture.pdfSha256,createHash('sha256').update(pdf).digest('hex'));assert.ok(fixture.raw.includes('Content-ID: <earnalism-logo>'));assert.ok(fixture.raw.includes('reader@example.invalid'));assert.throws(()=>makeEmailFixture(sample,Buffer.from('not pdf')));
});
