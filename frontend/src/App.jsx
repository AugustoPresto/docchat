import { useEffect, useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { listDocuments, checkHealth } from './services/api';

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
function EmptyState({ health }) {
  const isCloud = health?.provider === 'groq' || health?.provider === 'openai';

  return (
    <div className="empty-state">
      <div className="empty-state-orb">🧠</div>
      <h2>Chat with your documents</h2>
      <p>
        Upload any PDF and ask questions in plain language.
        The AI reads the document and answers using only its content —
        {isCloud ? (
          <strong> private, secure, and fast.</strong>
        ) : (
          <strong> everything runs locally on your machine.</strong>
        )}
      </p>
      <div className="feature-chips">
        {(isCloud
          ? ['🔒 100% secure', `☁️ Powered by ${health?.provider?.toUpperCase()}`, '🔍 RAG-based search', '📄 Max 100MB PDF']
          : ['🔒 100% private', '🦙 Powered by Ollama', '🔍 RAG-based search', '📄 Any PDF']
        ).map((f) => (
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
  const [health, setHealth] = useState(null);
  const [healthStatus, setHealthStatus] = useState('loading');

  // Poll health status and load documents once online
  useEffect(() => {
    let active = true;
    let timeoutId;

    const performCheck = () => {
      checkHealth()
        .then((data) => {
          if (!active) return;
          setHealth(data);
          setHealthStatus('ok');

          // Backend is awake, load/refresh the documents list
          listDocuments()
            .then((docData) => {
              if (active) setDocuments(docData.documents);
            })
            .catch(() => {/* ignore transient failures */});

          // Poll less frequently (60s) once successfully connected
          timeoutId = setTimeout(performCheck, 60000);
        })
        .catch(() => {
          if (!active) return;
          setHealthStatus('error');
          // Retry every 15 seconds until the backend wakes up
          timeoutId = setTimeout(performCheck, 15000);
        });
    };

    performCheck();

    return () => {
      active = false;
      clearTimeout(timeoutId);
    };
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
        health={health}
        healthStatus={healthStatus}
      />

      <main className="main-content">
        {activeDoc ? (
          <ChatInterface
            key={activeDoc.id}
            document={activeDoc}
            onToast={addToast}
          />
        ) : (
          <EmptyState health={health} />
        )}
      </main>

      <ToastContainer toasts={toasts} />
    </div>
  );
}
