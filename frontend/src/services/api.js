import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const ROOT_URL = BASE_URL.replace(/\/api\/v1\/?$/, '');

// crypto.randomUUID only exists in secure contexts (https / localhost).
export const randomId = () =>
  globalThis.crypto?.randomUUID?.() ??
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;

// ── Anonymous client id (no login) ───────────────────────────────────────────
// Lets the public demo show each visitor only their own documents.
function getClientId() {
  const KEY = 'docchat-client-id';
  try {
    let id = localStorage.getItem(KEY);
    if (!id) {
      id = randomId();
      localStorage.setItem(KEY, id);
    }
    return id;
  } catch {
    // Storage blocked (private mode): fall back to a per-tab id.
    getClientId.fallback ||= randomId();
    return getClientId.fallback;
  }
}

const clientHeaders = () => ({ 'X-Client-Id': getClientId() });

// ── Server reachability ───────────────────────────────────────────────────────
// Every real request tells the UI whether the server answered, so the status
// badge follows what the user actually experiences (e.g. a chat that works
// means the server is online), not just the occasional /health check.
const reachabilityListeners = new Set();
export const onServerReachability = (listener) => {
  reachabilityListeners.add(listener);
  return () => reachabilityListeners.delete(listener);
};
const reportReachable = (reachable) => reachabilityListeners.forEach((fn) => fn(reachable));

// No response at all, or the host's proxy saying the app isn't up (cold start, deploy).
const GATEWAY_ERRORS = [502, 503, 504];
const isUnreachable = (error) => !error.response || GATEWAY_ERRORS.includes(error.response.status);

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // generous: a free/sleeping server can take ~1 min to wake up
});
api.interceptors.request.use((config) => {
  Object.assign(config.headers, clientHeaders());
  return config;
});
api.interceptors.response.use(
  (response) => {
    reportReachable(true);
    return response;
  },
  (error) => {
    if (!axios.isCancel(error)) reportReachable(!isUnreachable(error));
    return Promise.reject(error);
  },
);

// ── Documents ─────────────────────────────────────────────────────────────────
// Returns immediately with status "processing"; indexing continues on the server.
export const uploadDocument = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post('/documents/upload', formData, {
    timeout: 0, // no timeout: the upload itself may be slow on a bad connection
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });
  return data;
};

export const listDocuments = async () => {
  const { data } = await api.get('/documents/');
  return data;
};

export const deleteDocument = async (docId) => {
  await api.delete(`/documents/${docId}`);
};

// ── Chat (streaming) ──────────────────────────────────────────────────────────
// Calls onSources(list) once, then onToken(text) for each piece of the answer.
export const streamMessage = async (documentId, message, conversationHistory, { onSources, onToken, signal }) => {
  let response;
  try {
    response = await fetch(`${BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...clientHeaders() },
      body: JSON.stringify({
        document_id: documentId,
        message,
        conversation_history: conversationHistory,
      }),
      signal,
    });
  } catch (error) {
    if (error.name !== 'AbortError') reportReachable(false);
    throw error;
  }
  reportReachable(!GATEWAY_ERRORS.includes(response.status));

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch { /* not JSON */ }
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const handle = (line) => {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.type === 'sources') onSources?.(event.sources);
    else if (event.type === 'token') onToken?.(event.content);
    else if (event.type === 'error') throw new Error(event.detail);
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    lines.forEach(handle);
  }
  handle(buffer);
};

// ── Health ────────────────────────────────────────────────────────────────────
export const checkHealth = async () => {
  const { data } = await axios.get(`${ROOT_URL}/health`, { timeout: 120000 });
  // A host's "waking up" HTML page can come back as 200: only trust our JSON.
  if (data?.status !== 'ok') throw new Error('Unexpected /health response');
  return data;
};

export default api;
