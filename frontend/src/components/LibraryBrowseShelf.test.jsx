import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import LibraryBrowseShelf from './LibraryBrowseShelf';

let host;
let root;
const books = Array.from({ length: 30 }, (_, index) => ({ slug: `edition-${index}`, title: `Edition ${index}` }));
const renderBook = book => <article><a href={`/book/${book.slug}`}>{book.title}</a></article>;
const render = list => act(() => root.render(<LibraryBrowseShelf title="Available to read" copy="Books" books={list} renderBook={renderBook} />));

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  host = document.createElement('div');
  document.body.appendChild(host);
  root = createRoot(host);
});
afterEach(() => { act(() => root.unmount()); host.remove(); });

test('metadata refresh preserves expanded editions and their reading links', () => {
  render(books);
  act(() => host.querySelector('button').click());
  expect(host.querySelectorAll('a')).toHaveLength(20);
  expect(document.activeElement.getAttribute('href')).toBe('/book/edition-10');
  render(books.map(book => ({ ...book, title: `${book.title} refreshed` })));
  expect(host.querySelectorAll('a')).toHaveLength(20);
  expect(host.querySelector('a').textContent).toBe('Edition 0 refreshed');
  act(() => host.querySelector('button').click());
  expect(host.querySelectorAll('a')).toHaveLength(30);
  expect(host.querySelector('button')).toBeNull();
  expect(document.activeElement.getAttribute('href')).toBe('/book/edition-20');
});

test('a changed edition order starts the new collection at its first page', () => {
  render(books);
  act(() => host.querySelector('button').click());
  render([...books].reverse());
  expect(host.querySelectorAll('a')).toHaveLength(10);
  expect(host.querySelector('a').getAttribute('href')).toBe('/book/edition-29');
});
