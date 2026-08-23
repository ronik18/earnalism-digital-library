import axios from 'axios';
import { API, USER_TOKEN_KEY } from './api';

const DEVICE_KEY = 'earnalism_reading_pass_device_v1';

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
  const response = await axios.get(`${API}/reading-pass/books/${encodeURIComponent(bookSlug)}/manifest`);
  return response.data;
}

export async function getReadingPassConfig() {
  const response = await axios.get(`${API}/reading-pass/config`);
  return response.data;
}

export async function getReadingPassDevices() {
  const response = await axios.get(
    `${API}/reading-pass/devices`,
    { headers: authHeaders() },
  );
  return response.data?.devices || [];
}

export async function getReadingPassPosition({ contentType, contentId }) {
  const response = await axios.get(
    `${API}/reading-pass/positions/${encodeURIComponent(contentType)}/${encodeURIComponent(contentId)}`,
    { headers: authHeaders() },
  );
  return response.data;
}

export async function revokeReadingPassDevice(sessionOrDeviceId) {
  const response = await axios.delete(
    `${API}/reading-pass/devices/${encodeURIComponent(sessionOrDeviceId)}`,
    { headers: authHeaders() },
  );
  return response.data;
}

export async function getReadingPassPage(bookSlug, pageIndex, lease = null) {
  const headers = { ...authHeaders() };
  if (lease?.sessionId && lease?.token) {
    headers['X-Reading-Pass-Session'] = lease.sessionId;
    headers['X-Reading-Pass-Lease'] = lease.token;
  }
  const response = await axios.get(
    `${API}/reading-pass/books/${encodeURIComponent(bookSlug)}/pages/${Number(pageIndex)}`,
    { headers },
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
    { headers: authHeaders(), withCredentials: true },
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
    { headers: authHeaders(), withCredentials: true },
  );
  return response.data;
}

export async function renewReadingPassLease({ lease, sequence, active, playbackState = '' }) {
  const response = await axios.post(
    `${API}/reading-pass/leases/renew`,
    {
      session_id: lease.sessionId,
      lease_version: lease.version,
      sequence,
      idempotency_key: `${lease.sessionId}:${sequence}:${globalThis.crypto?.randomUUID?.() || Date.now()}`,
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
    },
  );
  return response.data;
}

export async function endReadingPassSession(lease, reason = 'user_end') {
  if (!lease?.sessionId) return null;
  const response = await axios.post(
    `${API}/reading-pass/sessions/end`,
    { session_id: lease.sessionId, reason },
    { headers: authHeaders(), withCredentials: true },
  );
  return response.data;
}

export async function saveReadingPassPosition({ bookSlug, pageIndex, chapterId = '', version = 0 }) {
  const response = await axios.put(
    `${API}/reading-pass/positions`,
    {
      content_type: 'text',
      content_id: bookSlug,
      position: { canonical_page_index: Number(pageIndex), chapter_id: chapterId },
      version,
    },
    { headers: authHeaders() },
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
    { headers: authHeaders() },
  );
  return response.data;
}
