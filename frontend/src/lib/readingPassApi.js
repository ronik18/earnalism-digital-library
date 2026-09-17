import axios from 'axios';
import { API, USER_TOKEN_KEY } from './api';

const DEVICE_KEY = 'earnalism_reading_pass_device_v1';
// Bound every request that can hold the reader's navigation or settlement queue.
// A timeout reports an unknown outcome; it never authorizes access or retries a debit.
const REQUEST_TIMEOUT_MS = 15000;
const LEASE_TIMEOUT_MS = 8000;

function authHeaders() {
  const token = localStorage.getItem(USER_TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function readingPassDeviceId() {
  const existing = localStorage.getItem(DEVICE_KEY);
  if (existing) return existing;
  const generated = globalThis.crypto?.randomUUID?.() || `device-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  localStorage.setItem(DEVICE_KEY, generated);
  return generated;
}

export function readingPassError(error) {
  const detail = error?.response?.data?.detail;
  if (detail && typeof detail === 'object') return detail;
  return {
    code: error?.response?.status === 401 ? 'AUTH_REQUIRED' : 'CONNECTING',
    message: typeof detail === 'string' ? detail : 'Reading Pass could not be verified.',
  };
}

export async function getReadingPassManifest(bookSlug) {
  const response = await axios.get(`${API}/reading-pass/books/${encodeURIComponent(bookSlug)}/manifest`, { timeout: REQUEST_TIMEOUT_MS });
  return response.data;
}

export async function getReadingPassConfig() {
  const response = await axios.get(`${API}/reading-pass/config`, { timeout: REQUEST_TIMEOUT_MS });
  return response.data;
}

export async function getReadingPassDevices() {
  const response = await axios.get(
    `${API}/reading-pass/devices`,
    { headers: authHeaders(), timeout: REQUEST_TIMEOUT_MS },
  );
  return response.data?.devices || [];
}

export async function getReadingPassPosition({ contentType, contentId }) {
  const response = await axios.get(
    `${API}/reading-pass/positions/${encodeURIComponent(contentType)}/${encodeURIComponent(contentId)}`,
    { headers: authHeaders(), timeout: REQUEST_TIMEOUT_MS },
  );
  return response.data;
}

export async function revokeReadingPassDevice(sessionOrDeviceId) {
  const response = await axios.delete(
    `${API}/reading-pass/devices/${encodeURIComponent(sessionOrDeviceId)}`,
    { headers: authHeaders(), timeout: REQUEST_TIMEOUT_MS },
  );
  return response.data;
}

export async function getReadingPassPage(bookSlug, pageIndex, lease = null, { signal, timeoutMs = REQUEST_TIMEOUT_MS } = {}) {
  const headers = { ...authHeaders() };
  if (lease?.sessionId && lease?.token) {
    headers['X-Reading-Pass-Session'] = lease.sessionId;
    headers['X-Reading-Pass-Lease'] = lease.token;
  }
  const response = await axios.get(
    `${API}/reading-pass/books/${encodeURIComponent(bookSlug)}/pages/${Number(pageIndex)}`,
    { headers, signal, timeout: timeoutMs },
  );
  return response.data;
}

export async function startReadingPassSession({ bookSlug, pageIndex, transfer = false }) {
  const response = await axios.post(
    `${API}/reading-pass/sessions/${transfer ? 'transfer' : 'start'}`,
    {
      device_id: readingPassDeviceId(),
      device_label: `${navigator.platform || 'Web'} · ${navigator.userAgent.includes('Mobile') ? 'Mobile' : 'Browser'}`,
      content_type: 'text',
      content_id: bookSlug,
      canonical_page_index: Number(pageIndex),
    },
    { headers: authHeaders(), withCredentials: true, timeout: REQUEST_TIMEOUT_MS },
  );
  return response.data;
}

export async function getReadingPassAudioPreview(bookSlug) {
  return {
    book_slug: bookSlug,
    duration_seconds: 0,
    audio_url: '',
  };
}

export async function startReadingPassAudioSession({ bookSlug, positionSeconds = 0, transfer = false }) {
  const response = await axios.post(
    `${API}/reading-pass/sessions/${transfer ? 'transfer' : 'start'}`,
    {
      device_id: readingPassDeviceId(),
      device_label: `${navigator.platform || 'Web'} · ${navigator.userAgent.includes('Mobile') ? 'Mobile' : 'Browser'}`,
      content_type: 'audio',
      content_id: bookSlug,
      media_position_seconds: Math.max(0, Number(positionSeconds) || 0),
    },
    { headers: authHeaders(), withCredentials: true, timeout: REQUEST_TIMEOUT_MS },
  );
  return response.data;
}

export async function renewReadingPassLease({ lease, sequence, active, playbackState = '', idempotencyKey }) {
  const response = await axios.post(
    `${API}/reading-pass/leases/renew`,
    {
      session_id: lease.sessionId,
      lease_version: lease.version,
      sequence,
      idempotency_key: idempotencyKey || `${lease.sessionId}:${sequence}:${globalThis.crypto?.randomUUID?.() || Date.now()}`,
      active,
      playback_state: playbackState,
    },
    {
      headers: {
        ...authHeaders(),
        'X-Reading-Pass-Session': lease.sessionId,
        'X-Reading-Pass-Lease': lease.token,
      },
      withCredentials: true,
      timeout: LEASE_TIMEOUT_MS,
    },
  );
  return response.data;
}

export async function endReadingPassSession(lease, reason = 'user_end') {
  if (!lease?.sessionId) return null;
  const response = await axios.post(
    `${API}/reading-pass/sessions/end`,
    { session_id: lease.sessionId, reason },
    { headers: authHeaders(), withCredentials: true, timeout: REQUEST_TIMEOUT_MS },
  );
  return response.data;
}

export async function saveReadingPassPosition({ bookSlug, pageIndex, chapterId = '', segmentationVersion = '', manifestVersion = '', version = 0 }) {
  const response = await axios.put(
    `${API}/reading-pass/positions`,
    {
      content_type: 'text',
      content_id: bookSlug,
      position: { canonical_page_index: Number(pageIndex), chapter_id: chapterId },
      publication_segmentation_version: segmentationVersion || undefined,
      publication_manifest_version: manifestVersion || undefined,
      version,
    },
    { headers: authHeaders(), timeout: REQUEST_TIMEOUT_MS },
  );
  return response.data;
}

export async function saveReadingPassAudioPosition({ bookSlug, positionSeconds, version = 0 }) {
  const response = await axios.put(
    `${API}/reading-pass/positions`,
    {
      content_type: 'audio',
      content_id: bookSlug,
      position: { media_position_seconds: Math.max(0, Number(positionSeconds) || 0) },
      version,
    },
    { headers: authHeaders(), timeout: REQUEST_TIMEOUT_MS },
  );
  return response.data;
}
