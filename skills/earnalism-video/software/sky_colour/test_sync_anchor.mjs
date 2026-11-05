import assert from 'node:assert/strict';
import {sceneKinds,requiredMarks,assertTimeline} from './model.mjs';
const scenes=sceneKinds.map((scene,i)=>({scene,start:i*15,end:(i+1)*15,marks:Object.fromEntries(requiredMarks[scene].map((key,j)=>[key,j+1]))}));
const props={duration:90,scenes};
assertTimeline(props); // Old accepted data without the optional marker stays valid.
scenes[1].marks.scatter=1.5;assertTimeline(props);
for(const invalid of [NaN,-1,2,3,Infinity]){
 scenes[1].marks.scatter=invalid;
 assert.throws(()=>assertTimeline(props),/first-scatter anchor/);
}
console.log('PASS: optional first-cause marker is finite, in order and compatible with unchanged earlier timelines');
