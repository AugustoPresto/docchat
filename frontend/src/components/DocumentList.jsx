import { Trash2 } from 'lucide-react';
import { deleteDocument } from '../services/api';

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

const STAGE_LABEL = {
  queued: 'Waiting in queue…',
  reading: 'Reading pages…',
  indexing: 'Indexing…',
};

function DocMeta({ doc }) {
  if (doc.status === 'processing') {
    return (
      <div className="doc-processing">
        <div className="doc-meta">{STAGE_LABEL[doc.stage] || 'Processing…'} {doc.progress}%</div>
        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${Math.max(doc.progress, 3)}%` }} />
        </div>
      </div>
    );
  }
  if (doc.status === 'error') {
    return <div className="doc-meta doc-meta-error" title={doc.error}>⚠️ {doc.error}</div>;
  }
  return (
    <div className="doc-meta">
      {doc.page_count}p · {doc.chunk_count} chunks · {formatBytes(doc.size_bytes)} · {formatDate(doc.uploaded_at)}
    </div>
  );
}

export default function DocumentList({ documents, activeDocId, onSelect, onDeleted, onToast }) {
  if (!documents.length) {
    return (
      <div className="empty-docs">
        <span className="empty-docs-icon">🗂️</span>
        No documents yet.<br />Upload a PDF to get started.
      </div>
    );
  }

  const handleDelete = async (e, docId, docName) => {
    e.stopPropagation();
    if (!confirm(`Delete "${docName}"?`)) return;
    try {
      await deleteDocument(docId);
      onDeleted(docId);
      onToast('info', `🗑️ "${docName}" removed`);
    } catch {
      onToast('error', 'Failed to delete document.');
    }
  };

  return (
    <div className="doc-list">
      {documents.map((doc) => {
        const ready = doc.status === 'ready';
        return (
          <div
            key={doc.id}
            className={`doc-item ${doc.id === activeDocId ? 'active' : ''} ${ready ? '' : 'disabled'}`}
            onClick={() => ready && onSelect(doc)}
            id={`doc-item-${doc.id}`}
            title={doc.filename}
            role="button"
            tabIndex={ready ? 0 : -1}
            aria-disabled={!ready}
            onKeyDown={(e) => {
              if (ready && (e.key === 'Enter' || e.key === ' ')) {
                e.preventDefault();
                onSelect(doc);
              }
            }}
          >
            <span className="doc-icon">{doc.status === 'processing' ? '⏳' : '📄'}</span>
            <div className="doc-info">
              <div className="doc-name">{doc.filename}</div>
              <DocMeta doc={doc} />
            </div>
            <button
              className="doc-delete-btn"
              onClick={(e) => handleDelete(e, doc.id, doc.filename)}
              id={`delete-doc-${doc.id}`}
              title="Delete document"
              aria-label={`Delete ${doc.filename}`}
            >
              <Trash2 size={13} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
