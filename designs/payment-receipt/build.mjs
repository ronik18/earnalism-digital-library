import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {renderReceipt,renderEmail,emailText} from './renderer.mjs';
const d=JSON.parse(readFileSync(new URL('./sample.v1.json',import.meta.url)));
mkdirSync(new URL('./output',import.meta.url),{recursive:true});
for(const [name,content] of [['receipt.html',renderReceipt(d)],['email.html',renderEmail(d,{inlineLogo:true})],['email.txt',emailText(d)]]) writeFileSync(new URL('./output/'+name,import.meta.url),content);
console.log('Built synthetic receipt and email. No sending capability.');
