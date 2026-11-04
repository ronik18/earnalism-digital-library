import { useLayoutEffect, useRef } from 'react';
import { X } from 'lucide-react';

const FOCUSABLE = 'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export default function ReaderDialog({ id, label, onClose, returnFocus, children }) {
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useLayoutEffect(() => {
    const dialog = dialogRef.current;
    const trigger = returnFocus?.current || document.activeElement;
    if (typeof dialog.showModal === 'function') {
      try { dialog.showModal(); } catch { dialog.setAttribute('open', ''); }
    } else dialog.setAttribute('open', '');
    const containFocus = event => {
      if (!dialog.contains(event.target)) (dialog.querySelector(FOCUSABLE) || dialog).focus({ preventScroll: true });
    };
    document.addEventListener('focusin', containFocus);
    (dialog.querySelector(FOCUSABLE) || dialog).focus({ preventScroll: true });
    return () => {
      document.removeEventListener('focusin', containFocus);
      if (dialog.open && typeof dialog.close === 'function') dialog.close();
      if (trigger instanceof HTMLElement && trigger.isConnected) {
        trigger.focus({ preventScroll: true });
        // React may not have removed the reading surface's inert attribute yet.
        // Native focus ignores inert targets; retry after that commit, without
        // stealing focus from a newer sheet, navigation or focus-mode control.
        Promise.resolve().then(() => {
          if (!trigger.isConnected || trigger.closest('[inert]') || document.querySelector('dialog[open]')) return;
          const active = document.activeElement;
          if (active && active !== document.body && active !== document.documentElement && active.isConnected) return;
          trigger.focus({ preventScroll: true });
        });
      }
    };
  }, [returnFocus]);
  const onKeyDown = event => {
    // Reader page-turn shortcuts never consume a dialog's arrows or Escape.
    event.stopPropagation();
    if (event.key === 'Escape') { event.preventDefault(); closeRef.current(); return; }
    if (event.key !== 'Tab') return;
    const focusable = [...dialogRef.current.querySelectorAll(FOCUSABLE)].filter(node => node.tabIndex >= 0 && !node.closest('[hidden], [inert]'));
    const first = focusable[0]; const last = focusable.at(-1);
    if (!first) { event.preventDefault(); dialogRef.current.focus(); }
    else if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  };
  return <dialog ref={dialogRef} id={id} className="reader-folio__dialog" aria-labelledby={`${id}-title`} aria-modal="true" tabIndex={-1}
    onCancel={event => { event.preventDefault(); closeRef.current(); }} onKeyDown={onKeyDown}
    onClick={event => { if (event.target === event.currentTarget) {
      const bounds = event.currentTarget.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeRef.current();
    } }}>
    <header className="reader-folio__dialog-bar"><h2 id={`${id}-title`}>{label}</h2><button type="button" onClick={onClose} aria-label={`Close ${label.toLowerCase()}`}><X size={20} aria-hidden="true" /></button></header>
    <div className="reader-folio__dialog-body">{children}</div>
  </dialog>;
}
