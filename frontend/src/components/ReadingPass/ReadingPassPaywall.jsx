import React, { useEffect, useRef } from 'react';
import { ArrowLeft, CreditCard, LogIn, RefreshCw, X } from 'lucide-react';
import './ReadingPass.css';

export default function ReadingPassPaywall({
  open,
  reason = 'PASS_REQUIRED',
  message,
  balanceSeconds = 0,
  activeSession,
  onClose,
  onBuy,
  onSignIn,
  onRegister,
  onPreview,
  onTransfer,
}) {
  const dialogRef = useRef(null);
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    closeRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose?.();
        return;
      }
      if (event.key !== 'Tab') return;
      const controls = Array.from(dialogRef.current?.querySelectorAll('button:not([disabled]),a[href]') || []);
      if (!controls.length) return;
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      previous?.focus?.();
    };
  }, [onClose, open]);

  if (!open) return null;
  const elsewhere = reason === 'SESSION_ACTIVE_ELSEWHERE';
  const paused = reason === 'PAUSED' || reason === 'LEASE_EXPIRED';
  const authRequired = reason === 'AUTH_REQUIRED';
  return (
    <div className="reading-pass-paywall" role="presentation">
      <div className="reading-pass-paywall__backdrop" aria-hidden="true" />
      <section ref={dialogRef} className="reading-pass-paywall__dialog" role="dialog" aria-modal="true" aria-labelledby="reading-pass-paywall-title" aria-describedby="reading-pass-paywall-description">
        <button ref={closeRef} type="button" className="reading-pass-paywall__close" onClick={onClose} aria-label="Close Reading Pass dialog"><X size={20} /></button>
        <span className="reading-pass-paywall__eyebrow">READING PASS</span>
        <h2 id="reading-pass-paywall-title">{elsewhere ? 'Continue on this device?' : 'Continue with Reading Pass.'}</h2>
        <p id="reading-pass-paywall-description">{message || 'Sign in and add reading time to continue. Your place is already saved.'}</p>
        <div className="reading-pass-paywall__balance"><span>Current balance</span><strong>{Math.max(0, Number(balanceSeconds) || 0)} seconds</strong></div>
        {elsewhere && activeSession && (
          <div className="reading-pass-paywall__device">
            <strong>{activeSession.device_label || 'Another device'}</strong>
            <span>{activeSession.content_type || 'Reading'} is currently active</span>
          </div>
        )}
        <div className="reading-pass-paywall__actions">
          {elsewhere || paused ? (
            <button type="button" className="reading-pass-paywall__primary" onClick={onTransfer}><RefreshCw size={18} />{elsewhere ? 'Continue on this device' : 'Resume reading'}</button>
          ) : (
            <button type="button" className="reading-pass-paywall__primary" onClick={onBuy}><CreditCard size={18} />Buy Reading Pass</button>
          )}
          {authRequired && <button type="button" onClick={onSignIn}><LogIn size={18} />Sign in</button>}
          {authRequired && <button type="button" onClick={onRegister}>Register</button>}
          <button type="button" onClick={onPreview}><ArrowLeft size={18} />Return to the first 3 pages</button>
        </div>
      </section>
    </div>
  );
}
