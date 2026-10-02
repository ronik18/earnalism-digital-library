const { publicMetadataKeys, validPublicTextLicense } = require('../lib/public-metadata-policy');
function book() {
  return {slug:'licensed-title', text_license:{schema_version:'earnalism.text-license.v1',slug:'licensed-title',license:'CC-BY-SA-4.0',license_url:'https://creativecommons.org/licenses/by-sa/4.0/',attribution:'Contributors',changes:'Formatting adapted',scope:'Transcription only',disclaimer:'No warranties',source_url:'https://bn.wikisource.org/w/index.php?oldid=123',contributors_url:'https://bn.wikisource.org/w/index.php?action=history'}};
}
test('exact public license exception preserves every other private key and input', () => {
 const b=book(); const before=JSON.stringify(b);
 expect(validPublicTextLicense(b)).toBe(true); expect(publicMetadataKeys([b])).not.toContain('source_url'); expect(JSON.stringify(b)).toBe(before);
 b.source_url='https://private.example'; b.text_license.private_notes='internal'; b.text_license.extra={source_url:'https://private.example'};
 expect(publicMetadataKeys(b).filter(k=>k==='source_url')).toHaveLength(2); expect(publicMetadataKeys(b)).toContain('private_notes');
});
test.each([
 ['schema_version','wrong'],['slug','another-title'],['license','UNKNOWN'],['license_url','https://evil.example/'],['attribution',''],
 ['source_url','https://evil.example/'],['source_url','http://bn.wikisource.org/'],['source_url','https://user:password@bn.wikisource.org/'],
 ['source_url','https://bn.wikisource.org:444/'],['contributors_url','https://evil.example/'],['contributors_url','https://user:password@en.wikisource.org/'],
])('invalid license %s=%s receives no privacy exception',(key,value)=>{
 const b=book();b.text_license[key]=value;expect(validPublicTextLicense(b)).toBe(false);expect(publicMetadataKeys(b)).toContain('source_url');
});
test('CC0 accepts only exact permitted source paths, with both URLs verified',()=>{
 const b=book();Object.assign(b.text_license,{license:'CC0-1.0',license_url:'https://creativecommons.org/publicdomain/zero/1.0/',source_url:'https://standardebooks.org/ebooks/example',contributors_url:'https://github.com/standardebooks/example'});
 expect(validPublicTextLicense(b)).toBe(true);b.text_license.contributors_url='https://github.com/unrelated/example';expect(validPublicTextLicense(b)).toBe(false);
});
test('nested arbitrary objects cannot borrow a sibling book license exception',()=>{
 const b=book();expect(publicMetadataKeys({wrapper:b})).toContain('source_url');
});
