const finiteNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export function audioTimestampStartMs(item = {}) {
  const milliseconds = finiteNumber(item.start_ms ?? item.startMs);
  if (milliseconds !== null) return Math.max(0, milliseconds);

  const seconds = finiteNumber(item.start ?? item.start_seconds ?? item.startSeconds);
  return seconds === null ? 0 : Math.max(0, seconds * 1000);
}

export function audioTimestampEndMs(item = {}) {
  const milliseconds = finiteNumber(item.end_ms ?? item.endMs);
  if (milliseconds !== null) return Math.max(0, milliseconds);

  const seconds = finiteNumber(item.end ?? item.end_seconds ?? item.endSeconds);
  return seconds === null ? audioTimestampStartMs(item) : Math.max(0, seconds * 1000);
}

export function normalizeAudioTimestamp(item = {}) {
  return {
    ...item,
    start_ms: audioTimestampStartMs(item),
    end_ms: audioTimestampEndMs(item),
  };
}
