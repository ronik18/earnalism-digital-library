import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const roots = [];
function render(element) { const container = document.createElement('div'); const root = createRoot(container); act(() => root.render(element)); roots.push(root); return { container }; }
afterEach(() => { roots.splice(0).forEach(root => act(() => root.unmount())); });
import { ReaderContent, readerSourceText } from './readerContent';

test.each(['(*kept in shorthand*)', '_Mem., get recipe for Mina._'])('balanced emphasis retains source coordinates: %s', raw => {
  const { container } = render(<ReaderContent html={`<p>${raw}</p>`} />);
  expect(container.querySelector('em')).not.toBeNull();
  expect(container.textContent).toBe(raw);
  expect(readerSourceText(`<p>${raw}</p>`)).toBe(raw);
  expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(2);
});
test.each(['“Café”—it’s unchanged…', '* * *', '*word', 'word_', 'a_b_c', '* padded *'])('ambiguous or literary text remains literal: %s', raw => {
  const { container } = render(<ReaderContent html={`<p>${raw}</p>`} />);
  expect(container.textContent).toBe(raw);
  expect(container.querySelector('em')).toBeNull();
});
test('structured emphasis is not reparsed', () => {
  const { container } = render(<ReaderContent html='<p><em>*literal*</em></p>' />);
  expect(container.querySelectorAll('em')).toHaveLength(1);
  expect(container.querySelector('.reader-v2__format-marker')).toBeNull();
});
