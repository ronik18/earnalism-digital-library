import React from 'react';
import { Clock, Plus } from 'lucide-react';
import './ReadingPass.css';

export function formatReadingPassTime(seconds = 0) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const remaining = value % 60;
  return [hours, minutes, remaining].map((part) => String(part).padStart(2, '0')).join(':');
}

export default function ReadingPassTimer({
  enabled,
  balanceSeconds = 0,
  status = 'Preview',
  contentType = 'Reading',
  onOpen,
  onTopUp,
}) {
  if (!enabled) return null;
  const consuming = status === 'Running';
  return (
    <aside className="reading-pass-timer" aria-label="Reading Pass status" data-status={status.toLowerCase().replaceAll(' ', '-')}>
      <button type="button" className="reading-pass-timer__main" onClick={onOpen} aria-label={`Reading Pass ${formatReadingPassTime(balanceSeconds)}, ${status}`}>
        <Clock size={16} aria-hidden="true" />
        <span className="reading-pass-timer__time" aria-hidden="true">{formatReadingPassTime(balanceSeconds)}</span>
        <span className="reading-pass-timer__state">
          <strong>{status}</strong>
          <small>{consuming ? contentType : 'Reading Pass'}</small>
        </span>
      </button>
      {onTopUp && (
        <button type="button" className="reading-pass-timer__topup" onClick={onTopUp} aria-label="Add Reading Pass time">
          <Plus size={17} aria-hidden="true" />
        </button>
      )}
    </aside>
  );
}
