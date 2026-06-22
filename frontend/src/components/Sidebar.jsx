import { useEffect, useState } from 'react';
import DocumentUpload from './DocumentUpload';
import DocumentList from './DocumentList';
import { checkHealth } from '../services/api';

export default function Sidebar({ documents, activeDocId, onUploaded, onSelect, onDeleted, onToast }) {
  const [health, setHealth] = useState(null);
  const [healthStatus, setHealthStatus] = useState('loading');

  useEffect(() => {
    checkHealth()
      .then((data) => { setHealth(data); setHealthStatus('ok'); })
      .catch(() => setHealthStatus('error'));
  }, []);

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">💬</div>
          <span className="logo-text">DocChat</span>
        </div>
        <div className="logo-tagline">Powered by Ollama · 100% local</div>
      </div>

      {/* Upload + Documents */}
      <div className="sidebar-section">
        <div className="section-label">Upload</div>
        <DocumentUpload onUploaded={onUploaded} onToast={onToast} />

        <div className="section-label" style={{ marginTop: '12px' }}>
          Documents ({documents.length})
        </div>
        <DocumentList
          documents={documents}
          activeDocId={activeDocId}
          onSelect={onSelect}
          onDeleted={onDeleted}
          onToast={onToast}
        />
      </div>

      {/* Ollama status bar */}
      <div className="status-bar">
        <div className={`status-dot ${healthStatus}`} />
        <span className="status-text">
          {healthStatus === 'loading' && 'Connecting to Ollama…'}
          {healthStatus === 'ok'      && 'Ollama connected'}
          {healthStatus === 'error'   && 'Ollama offline — start it first'}
        </span>
        {health && (
          <span className="status-model">{health.chat_model}</span>
        )}
      </div>
    </aside>
  );
}
