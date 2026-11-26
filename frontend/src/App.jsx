import { useEffect, useState, useCallback, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { listDocuments, checkHealth } from './services/api';
import { Menu } from 'lucide-react';

const PROCESSING_POLL_MS = 1500;
const HEALTH_RETRY_MS = 10000;
const HEALTH_STALE_MS = 5 * 60 * 1000;

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
  const maxMb = health?.max_upload_mb;

  return (
    <div className="empty-state">
      <div className="empty-state-orb">🧠</div>
      <h2>Chat with your documents</h2>
      <p>
        Upload any PDF and ask questions in plain language.
        The AI reads the document and answers using only its content —
        {isCloud ? (
          <strong> no sign-up needed, just drop a PDF.</strong>
        ) : (
          <strong> everything runs locally on your machine, even offline.</strong>
        )}
      </p>
      <div className="feature-chips">
        {(isCloud
          ? ['🙋 No login', `☁️ Powered by ${health?.provider?.toUpperCase()}`, '🔍 RAG-based search', `📄 PDF up to ${maxMb ?? '?'}MB`]
          : ['🔒 100% private', '🦙 Powered by Ollama', '📴 Works offline', '🔍 RAG-based search']
        ).map((f) => (
          <div key={f} className="chip">{f}</div>
        ))}
      </div>
      {isCloud && health?.doc_ttl_hours > 0 && (
        <p className="empty-state-note">
          Demo server: your documents are private to this browser and deleted after {health.doc_ttl_hours}h.
        </p>
      )}
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
  const [slowStart, setSlowStart] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  // Document to open automatically once its background indexing finishes
  const pendingOpenId = useRef(null);

  // Toast helper
  const addToast = useCallback((type, message) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000);
  }, []);

  // Health: check on load, retry while offline, re-check when the tab comes
  // back after a while. No continuous polling — that would keep a free
  // server awake (and billed) for as long as a tab is open.
  useEffect(() => {
    let active = true;
    let retryId;
    let lastOk = 0;
    const slowId = setTimeout(() => active && setSlowStart(true), 5000);

    const performCheck = () => {
      checkHealth()
        .then((data) => {
          if (!active) return;
          lastOk = Date.now();
          setHealth(data);
          setHealthStatus('ok');
          setSlowStart(false);
          clearTimeout(slowId);
          listDocuments()
            .then((docData) => active && setDocuments(docData.documents))
            .catch(() => {/* shown as empty list; retried on next check */});
        })
        .catch(() => {
          if (!active) return;
          setHealthStatus('error');
          retryId = setTimeout(performCheck, HEALTH_RETRY_MS);
        });
    };

    const onVisible = () => {
      if (document.visibilityState === 'visible' && Date.now() - lastOk > HEALTH_STALE_MS) {
        clearTimeout(retryId);
        performCheck();
      }
    };

    performCheck();
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      active = false;
      clearTimeout(retryId);
      clearTimeout(slowId);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);

  // While any document is being indexed, poll the list for progress.
  const hasProcessing = documents.some((d) => d.status === 'processing');
  useEffect(() => {
    if (!hasProcessing) return undefined;
    const id = setTimeout(async () => {
      let fresh;
      try {
        ({ documents: fresh } = await listDocuments());
      } catch {
        // Transient failure: a new array re-runs this effect, i.e. retries.
        setDocuments((prev) => [...prev]);
        return;
      }
      documents.forEach((old) => {
        if (old.status !== 'processing') return;
        const now = fresh.find((d) => d.id === old.id);
        if (now?.status === 'ready') {
          addToast('success', `✅ "${now.filename}" indexed — ${now.chunk_count} chunks ready`);
          if (pendingOpenId.current === now.id) {
            pendingOpenId.current = null;
            setActiveDoc(now);
            setIsSidebarOpen(false);
          }
        } else if (now?.status === 'error') {
          addToast('error', `❌ "${now.filename}": ${now.error}`);
        }
      });
      setDocuments(fresh);
    }, PROCESSING_POLL_MS);
    return () => clearTimeout(id);
  }, [documents, hasProcessing, addToast]);

  // Handlers
  const handleUploaded = (doc) => {
    setDocuments((prev) => [doc, ...prev]);
    pendingOpenId.current = doc.id;
  };

  const handleDeleted = (docId) => {
    setDocuments((prev) => prev.filter((d) => d.id !== docId));
    if (activeDoc?.id === docId) setActiveDoc(null);
  };

  return (
    <div className="app-layout">
      {isSidebarOpen && (
        <div className="sidebar-backdrop" onClick={() => setIsSidebarOpen(false)} />
      )}

      <Sidebar
        documents={documents}
        activeDocId={activeDoc?.id}
        onUploaded={handleUploaded}
        onSelect={(doc) => {
          setActiveDoc(doc);
          setIsSidebarOpen(false);
        }}
        onDeleted={handleDeleted}
        onToast={addToast}
        health={health}
        healthStatus={healthStatus}
        slowStart={slowStart}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      <main className="main-content">
        {activeDoc ? (
          <ChatInterface
            key={activeDoc.id}
            document={activeDoc}
            onToast={addToast}
            onToggleSidebar={() => setIsSidebarOpen(true)}
          />
        ) : (
          <div className="empty-wrapper">
            <div className="mobile-header">
              <button className="mobile-menu-btn" onClick={() => setIsSidebarOpen(true)} aria-label="Open menu">
                <Menu size={20} />
              </button>
              <div className="logo logo-compact">
                <div className="logo-icon">💬</div>
                <span className="logo-text">DocChat</span>
              </div>
            </div>
            <EmptyState health={health} />
          </div>
        )}
      </main>

      <ToastContainer toasts={toasts} />
    </div>
  );
}
