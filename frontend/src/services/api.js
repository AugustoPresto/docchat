import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2min — Ollama can be slow on first call
});

// ── Documents ─────────────────────────────────────────────────────────────────
export const uploadDocument = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
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

// ── Chat ──────────────────────────────────────────────────────────────────────
export const sendMessage = async (documentId, message, conversationHistory = []) => {
  const { data } = await api.post('/chat/', {
    document_id: documentId,
    message,
    conversation_history: conversationHistory,
  });
  return data;
};

// ── Health ────────────────────────────────────────────────────────────────────
export const checkHealth = async () => {
  const { data } = await axios.get(
    (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace('/api/v1', '') + '/health'
  );
  return data;
};

export default api;
