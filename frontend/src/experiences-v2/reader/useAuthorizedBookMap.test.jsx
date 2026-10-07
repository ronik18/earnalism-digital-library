import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import useAuthorizedBookMap from './useAuthorizedBookMap';
jest.mock('./useVisualPagination', () => () => ({pending:true,pages:[],signature:''}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const planA = {key:'a',chapterId:'a',chapterTitle:'One'};
const planB = {key:'b',chapterId:'b',chapterTitle:'Two'};
const chapter = {plan:planA,textLength:10,sources:[{page:1,start:0,end:10,revision:'hash-a'}]};
const pagination = {width:600,height:400,pending:false,pages:[{start:0,end:10}]};
let map;
function Harness({model}) {
  map = useAuthorizedBookMap({model,pagination,visualIndex:0,viewportRef:{current:null},typography:'fixed'});
  return <span>{map.total || 'unknown'}</span>;
}
let container,root;
beforeEach(() => {jest.useFakeTimers();container=document.createElement('div');document.body.append(container);root=createRoot(container);});
afterEach(() => {act(()=>root.unmount());container.remove();jest.useRealTimers();});
const render = model => act(()=>root.render(<Harness model={model}/>));
test('background work aborts and map is discarded when authorization changes', async () => {
  let signal; const load = jest.fn((plan,value) => {signal=value;return new Promise(()=>{});});
  const model = {authorizedChapter:chapter,authorizedBookPlans:[planA,planB],bookMapScope:'reader:session1',loadAuthorizedChapter:load};
  render(model);
  await act(async()=>{jest.runOnlyPendingTimers();});
  expect(load).toHaveBeenCalledTimes(1);expect(load.mock.calls[0][0]).toBe(planB);
  render({...model,bookMapScope:'preview',authorizedChapter:null,authorizedBookPlans:[],loadAuthorizedChapter:undefined});
  expect(signal.aborted).toBe(true);expect(map.options).toEqual([]);expect(map.total).toBeNull();
});
test('unmount cancels work and stale completion cannot restore protected grants', async () => {
  let signal,resolve;
  const load = jest.fn((plan,value)=>{signal=value;return new Promise(done=>{resolve=done;});});
  render({authorizedChapter:chapter,authorizedBookPlans:[planA,planB],bookMapScope:'reader:session',loadAuthorizedChapter:load});
  await act(async()=>{jest.runOnlyPendingTimers();});
  act(()=>root.unmount());expect(signal.aborted).toBe(true);
  await act(async()=>resolve({...chapter,plan:planB}));
  root=createRoot(container);
  render({authorizedChapter:null,authorizedBookPlans:[],bookMapScope:'preview'});
  expect(map.options).toEqual([]);
});
