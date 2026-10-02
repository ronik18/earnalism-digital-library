import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import LicensedTextNotice from './LicensedTextNotice';
const common = {schema_version:'earnalism.text-license.v1',slug:'test',attribution:'Actual contributors',changes:'Formatting only',scope:'Transcription only',disclaimer:'Other assets excluded'};
let container, root;
beforeEach(()=>{container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);});
afterEach(()=>{act(()=>root.unmount());container.remove();});
test('CC0 contributions do not acquire a false ShareAlike requirement',()=>{
 const text_license={...common,license:'CC0-1.0',license_url:'https://creativecommons.org/publicdomain/zero/1.0/',source_url:'https://standardebooks.org/ebooks/test',contributors_url:'https://github.com/standardebooks/test'};
 act(()=>root.render(<LicensedTextNotice book={{slug:'test',text_license}}/>));
 expect(container.textContent).toContain('CC0 1.0');expect(container.textContent).not.toContain('same licence');expect(container.textContent).not.toContain('CC BY-SA');
});
test('CC BY-SA preserves the actual ShareAlike notice',()=>{
 const text_license={...common,license:'CC-BY-SA-4.0',license_url:'https://creativecommons.org/licenses/by-sa/4.0/',source_url:'https://bn.wikisource.org/wiki/Test',contributors_url:'https://bn.wikisource.org/w/index.php?action=history'};
 act(()=>root.render(<LicensedTextNotice book={{slug:'test',text_license}}/>));
 expect(container.textContent).toContain('same licence');expect(container.textContent).toContain('CC BY-SA 4.0');
});
