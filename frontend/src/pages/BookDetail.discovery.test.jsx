import React, {act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import BookDetail from './BookDetail';
import {api} from '../lib/api';
jest.mock('react-router-dom',()=>{const {TextEncoder,TextDecoder}=require('util');globalThis.TextEncoder=TextEncoder;globalThis.TextDecoder=TextDecoder;return require('react-router');},{virtual:true});
jest.mock('../lib/api',()=>({api:{get:jest.fn()}}));
jest.mock('../hooks/useSEO',()=>()=>{});
jest.mock('../lib/funnelAnalytics',()=>({trackFunnelEvent:jest.fn(),trackPageAnalyticsView:jest.fn()}));
jest.mock('../components/BookCoverImage',()=>()=>null);
let container,root;
beforeEach(()=>{global.IS_REACT_ACT_ENVIRONMENT=true;container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);api.get.mockReset();});
afterEach(async()=>{await act(async()=>root.unmount());container.remove();});
const renderBook=async(book)=>{
 api.get.mockImplementation(url=>url.startsWith('/books/')?Promise.resolve({data:book}):Promise.reject({response:{status:401}}));
 await act(async()=>root.render(<MemoryRouter initialEntries={['/book/'+book.slug]}><Routes><Route path="/book/:slug" element={<BookDetail/>}/></Routes></MemoryRouter>));
};
test('Book detail uses the same corrected mystery discovery genre as Library, not stale category',async()=>{
 await renderBook({slug:'a-scandal-in-bohemia',title:'A Scandal in Bohemia',author:'Arthur Conan Doyle',category_slug:'gothic-fiction',public_json_ld_enabled:true,publication_status:'LIVE_APPROVED',reader_enabled:true});
 expect(container.querySelector('[data-testid="book-discovery-genres"]').textContent).toBe('mystery');
 expect(container.querySelector('a[href^="/listener/"]')).toBeNull();
 const schemas=[...document.querySelectorAll('script[type="application/ld+json"]')].map(e=>JSON.parse(e.textContent));
 expect(schemas.some(s=>s['@type']==='Book')).toBe(true);
 expect(schemas.find(s=>s['@type']==='Book').genre).toEqual(['mystery']);
 expect(schemas.filter(s=>s['@type']==='Book').every(s=>!Object.prototype.hasOwnProperty.call(s,'isAccessibleForFree'))).toBe(true);
});
test('exact accepted Bengali language is retained even with a transliterated display title',async()=>{
 await renderBook({slug:'radharani',title:'Radharani',author:'Bankim Chandra',category_slug:'literary-fiction',publication_status:'LIVE_APPROVED',reader_enabled:true});
 expect(container.textContent).toContain('Bengali');
 expect(container.querySelector('[data-testid="book-discovery-genres"]').textContent).toBe('literary fiction');
});
