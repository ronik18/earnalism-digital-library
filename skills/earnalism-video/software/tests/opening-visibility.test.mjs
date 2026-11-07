import test from 'node:test';
import assert from 'node:assert/strict';
import {subjectOpacity} from '../src/opening-visibility.mjs';
test('opening subject is visible from frame zero and stays visible',()=>{
 for(const t of [0,1/30,.5,2])assert.equal(subjectOpacity(t,0,true),1);
});
test('later scene entrances remain bounded instead of adding a global brightness jump',()=>{
 assert.equal(subjectOpacity(9,10,false),0);assert.equal(subjectOpacity(10,10,false),0);
 assert.equal(subjectOpacity(10.5,10,false),1);
});
