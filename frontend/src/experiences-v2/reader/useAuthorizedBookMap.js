import { useEffect, useMemo, useRef, useState } from 'react';
import useVisualPagination from './useVisualPagination';
import { measuredChapterEntry, bookPageDomain } from './authorizedBookMap';
import { transportAnchor } from './authorizedChapter';

export default function useAuthorizedBookMap({ model, pagination, visualIndex, viewportRef, typography }) {
  const sourceRef = useRef(null); const measureRef = useRef(null);
  const [state, setState] = useState({ key: '', entries: {}, failed: [] });
  const [candidate, setCandidate] = useState(null);
  const loadRef = useRef(model.loadAuthorizedChapter); loadRef.current = model.loadAuthorizedChapter;
  const plans = useMemo(() => model.authorizedBookPlans || [], [model.authorizedBookPlans]);
  const key = pagination.width && pagination.height
    ? `${model.bookMapScope || ''}|${pagination.width}:${pagination.height}|${typography}|${plans.map(plan => plan.key).join(';')}` : '';
  // Never return grants from another layout, edition, principal or lease.
  const entries = useMemo(() => state.key === key ? state.entries : {}, [state, key]);
  const background = useVisualPagination({ sourceRef, measureRef, viewportRef,
    revision: candidate ? `${key}:${candidate.revision}` : '', typography, authorizationScope: model.bookMapScope });
  useEffect(() => {
    setCandidate(null);
    setState({ key, entries: {}, failed: [] });
  }, [key]);
  useEffect(() => {
    if (!key || pagination.pending || pagination.error || !model.authorizedChapter) return;
    const entry = measuredChapterEntry(model.authorizedChapter, pagination.pages, offset => transportAnchor(model.authorizedChapter, offset));
    setState(previous => previous.key === key ? { ...previous, entries: { ...previous.entries, [entry.key]: entry } } : previous);
  }, [key, pagination.pending, pagination.error, pagination.pages, model.authorizedChapter]);
  useEffect(() => {
    if (!candidate || background.pending || (!background.error && background.signature.indexOf(`${key}:${candidate.revision}`) !== 0)) return;
    if (background.error) {
      setState(previous => previous.key === key ? { ...previous, failed: [...previous.failed, candidate.plan.key] } : previous);
    } else {
      const entry = measuredChapterEntry(candidate, background.pages, offset => transportAnchor(candidate, offset));
      setState(previous => previous.key === key ? { ...previous, entries: { ...previous.entries, [entry.key]: entry } } : previous);
    }
    setCandidate(null);
  }, [candidate, background.pending, background.signature, background.error, background.pages, key]);
  useEffect(() => {
    if (!key || pagination.pending || candidate || state.key !== key || !loadRef.current || !entries[model.authorizedChapter?.plan.key]) return undefined;
    const plan = plans.find(item => !entries[item.key] && !state.failed.includes(item.key));
    if (!plan) return undefined;
    const controller = new AbortController(); let cancelled = false;
    // One neighboring chapter at a time; current chapter always wins startup.
    const timer = setTimeout(() => {
      loadRef.current(plan, controller.signal).then(value => {
        if (!cancelled) setCandidate(value);
      }).catch(() => {
        if (!cancelled) setState(previous => previous.key === key ? { ...previous, failed: [...previous.failed, plan.key] } : previous);
      });
    }, 0);
    return () => { cancelled = true; clearTimeout(timer); controller.abort(); };
  }, [key, pagination.pending, candidate, state, entries, plans, model.authorizedChapter]);
  return { ...bookPageDomain(plans, entries, model.authorizedChapter?.plan.key, visualIndex),
    candidate: state.key === key ? candidate : null, sourceRef, measureRef };
}
