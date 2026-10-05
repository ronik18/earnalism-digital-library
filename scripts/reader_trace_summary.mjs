// Trace data stays in memory. Export durations/counts, never request arguments.
export function summarizeReaderTrace(events) {
  const complete = events.filter(e => e.ph === 'X' && Number.isFinite(e.dur));
  const layouts = complete.filter(e => e.name === 'Layout');
  const scripts = complete.filter(e => ['FunctionCall', 'EvaluateScript', 'RunMicrotasks'].includes(e.name));
  const sameThread = (a, b) => a.pid === b.pid && a.tid === b.tid;
  const forced = layouts.filter(e => e.args?.beginData?.stackTrace?.length || scripts.some(s => sameThread(s, e) && s.ts <= e.ts && s.ts + s.dur >= e.ts + e.dur));
  const main = layouts[0] || scripts[0];
  const tasks = complete.filter(e => ['RunTask', 'ThreadControllerImpl::RunTask'].includes(e.name) && (!main || sameThread(e, main)));
  const sum = rows => rows.reduce((n, e) => n + e.dur / 1000, 0);
  const max = rows => rows.reduce((n, e) => Math.max(n, e.dur / 1000), 0);
  return {
    forcedLayoutMethod: 'Layout with explicit script stack, or entirely nested in same-thread FunctionCall/EvaluateScript/RunMicrotasks; synchronous JS-attributed reflow, not every browser layout',
    forcedLayoutCount: forced.length, forcedLayoutMs: sum(forced),
    layoutsWithExplicitStack: layouts.filter(e => e.args?.beginData?.stackTrace?.length).length,
    layoutCount: layouts.length, layoutMs: sum(layouts), longestLayoutMs: max(layouts),
    styleMs: sum(complete.filter(e => e.name === 'UpdateLayoutTree')),
    paintMs: sum(complete.filter(e => e.name === 'Paint')),
    longestMainTaskMs: max(tasks), longMainTasks: tasks.filter(e => e.dur > 50000).map(e => ({ durationMs: e.dur / 1000 })),
    gcEvents: complete.filter(e => /GC|GarbageCollect/.test(e.name)).map(e => ({ name: e.name, durationMs: e.dur / 1000 })),
  };
}
