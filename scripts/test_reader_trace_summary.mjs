import test from 'node:test';
import assert from 'node:assert/strict';
import { summarizeReaderTrace } from './reader_trace_summary.mjs';
const event = (name, ts, dur, extra = {}) => ({ name, ts, dur, ph: 'X', pid: 1, tid: 2, ...extra });
test('synchronous layout attribution excludes normal rendering and other threads', () => {
  const r = summarizeReaderTrace([event('FunctionCall', 10, 100), event('Layout', 20, 30), event('Layout', 200, 30), event('Layout', 20, 30, { tid: 3 })]);
  assert.equal(r.layoutCount, 3); assert.equal(r.forcedLayoutCount, 1); assert.equal(r.forcedLayoutMs, .03);
});
test('nested script frames do not double count layout; explicit stacks count once', () => {
  const r = summarizeReaderTrace([event('FunctionCall', 0, 100), event('RunMicrotasks', 0, 100), event('Layout', 20, 30), event('Layout', 200, 20, { args: { beginData: { stackTrace: [{ url: 'secret-must-not-export' }] } } })]);
  assert.equal(r.forcedLayoutCount, 2); assert.equal(r.layoutsWithExplicitStack, 1); assert.ok(!JSON.stringify(r).includes('secret-must-not-export'));
});
test('Chrome controller task name is measured on the layout main thread', () => {
  const r = summarizeReaderTrace([event('Layout', 0, 10), event('ThreadControllerImpl::RunTask', 0, 60000), event('ThreadControllerImpl::RunTask', 0, 90000, { tid: 3 })]);
  assert.equal(r.longestMainTaskMs, 60); assert.equal(r.longMainTasks.length, 1);
});
