import { useEffect, useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { listDocuments } from './services/api';

// ── Toast ─────────────────────────────────────────────────────────────────────
function ToastContainer({ toasts }) {
  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.type}`}>
          {t.message}
        </div>
      ))}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-state-orb">🧠</div>
      <h2>Chat with your documents</h2>
      <p>
        Upload any PDF and ask questions in plain language.
        The AI reads the document and answers using only its content —
        <strong> everything runs locally on your machine.</strong>
      </p>
      <div className="feature-chips">
        {['🔒 100% private', '🦙 Powered by Ollama', '🔍 RAG-based search', '📄 Any PDF'].map((f) => (
          <div key={f} className="chip">{f}</div>
        ))}
      </div>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [documents, setDocuments] = useState([]);
  const [activeDoc, setActiveDoc] = useState(null);
  const [toasts, setToasts] = useState([]);

  // Load documents on mount
  useEffect(() => {
    listDocuments()
      .then((data) => setDocuments(data.documents))
      .catch(() => {/* silently ignore on startup */});
  }, []);

  // Toast helper
  const addToast = useCallback((type, message) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  // Handlers
  const handleUploaded = (doc) => {
    setDocuments((prev) => [doc, ...prev]);
    setActiveDoc(doc);
  };

  const handleDeleted = (docId) => {
    setDocuments((prev) => prev.filter((d) => d.id !== docId));
    if (activeDoc?.id === docId) setActiveDoc(null);
  };

  return (
    <div className="app-layout">
      <Sidebar
        documents={documents}
        activeDocId={activeDoc?.id}
        onUploaded={handleUploaded}
        onSelect={setActiveDoc}
        onDeleted={handleDeleted}
        onToast={addToast}
      />

      <main className="main-content">
        {activeDoc ? (
          <ChatInterface
            key={activeDoc.id}
            document={activeDoc}
            onToast={addToast}
          />
        ) : (
          <EmptyState />
        )}
      </main>

      <ToastContainer toasts={toasts} />
    </div>
  );
}
