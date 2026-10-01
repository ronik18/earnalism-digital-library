import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import SecureReader from './SecureReader';
globalThis.IS_REACT_ACT_ENVIRONMENT=true;
let container,root;
beforeEach(()=>{global.fetch=jest.fn().mockResolvedValue({ok:true});container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);});
afterEach(()=>{act(()=>root.unmount());container.remove();});
test('licensed delivered transcription permits copying and printing',()=>{act(()=>root.render(<SecureReader licensedText html='<p>Licensed prose</p>' footerText='CC BY-SA 4.0' licenseAttribution={<p>Credit to contributors</p>} />));const section=container.querySelector('section');expect(section.className).toContain('secure-reader--licensed-text');const copy=new Event('copy',{bubbles:true,cancelable:true});act(()=>section.dispatchEvent(copy));expect(copy.defaultPrevented).toBe(false);const print=new KeyboardEvent('keydown',{key:'p',ctrlKey:true,bubbles:true,cancelable:true});document.dispatchEvent(print);expect(print.defaultPrevented).toBe(false);expect(container.textContent).toContain('Credit to contributors');expect(global.fetch).not.toHaveBeenCalled();});
test('unlicensed titles retain copy protection',()=>{act(()=>root.render(<SecureReader html='<p>Protected prose</p>' />));const copy=new Event('copy',{bubbles:true,cancelable:true});act(()=>container.querySelector('section').dispatchEvent(copy));expect(copy.defaultPrevented).toBe(true);expect(global.fetch).toHaveBeenCalledTimes(1);});
