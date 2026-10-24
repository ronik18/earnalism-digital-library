import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {validate,renderEmail,emailText} from './renderer.mjs';
export function makeEmailFixture(input,pdf) {
 const d=validate(input);
 if(!Buffer.isBuffer(pdf)||pdf.subarray(0,5).toString()!=='%PDF-') throw new TypeError('Rendered PDF bytes required');
 const logo=readFileSync(new URL('./assets/earnalism-brand-lockup.png',import.meta.url));
 const b64=b=>Buffer.from(b).toString('base64').match(/.{1,76}/g).join('\r\n');
 const part=(type,bytes,headers='')=>`Content-Type: ${type}\r\nContent-Transfer-Encoding: base64\r\n${headers}\r\n${b64(bytes)}\r\n`;
 const alt='earnalism-alternative-v1',related='earnalism-related-v1',mixed='earnalism-mixed-v1';
 // Unsent fixture: reserved .invalid recipient; owner-specified sender identity.
 // Live transport still requires a verified sender and is not implemented here.
 const raw=`From: Earnalism${d.sample ? ' Sample' : ''} <sales@reoenterprise.org>\r\nReply-To: sales@reoenterprise.org\r\nTo: reader@example.invalid\r\nSubject: ${d.sample ? 'SAMPLE - ' : ''}Earnalism payment receipt\r\nMIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary="${mixed}"\r\n\r\n--${mixed}\r\nContent-Type: multipart/related; boundary="${related}"\r\n\r\n--${related}\r\nContent-Type: multipart/alternative; boundary="${alt}"\r\n\r\n--${alt}\r\n${part('text/plain; charset=utf-8',emailText(d))}--${alt}\r\n${part('text/html; charset=utf-8',renderEmail(d))}--${alt}--\r\n--${related}\r\n${part('image/png',logo,'Content-ID: <earnalism-logo>\r\nContent-Disposition: inline; filename="earnalism-brand-lockup.png"\r\n')}--${related}--\r\n--${mixed}\r\n${part('application/pdf',pdf,`Content-Disposition: attachment; filename="${d.sample ? 'SAMPLE-' : ''}${d.receiptNumber}.pdf"\r\n`)}--${mixed}--\r\n`;
 return {raw,pdfSha256:createHash('sha256').update(pdf).digest('hex')};
}
if(process.argv[1]===new URL(import.meta.url).pathname){
 const d=JSON.parse(readFileSync(new URL('./sample.v1.json',import.meta.url)));
 const result=makeEmailFixture(d,readFileSync(new URL('./output/receipt.pdf',import.meta.url)));
 writeFileSync(new URL('./output/email-sample.eml',import.meta.url),result.raw);
 console.log(JSON.stringify({attachmentSha256:result.pdfSha256}));
}
