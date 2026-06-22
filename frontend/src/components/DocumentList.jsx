import { Trash2 } from 'lucide-react';
import { deleteDocument } from '../services/api';

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric',
  });
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
      {documents.map((doc) => (
        <div
          key={doc.id}
          className={`doc-item ${doc.id === activeDocId ? 'active' : ''}`}
          onClick={() => onSelect(doc)}
          id={`doc-item-${doc.id}`}
          title={doc.filename}
        >
          <span className="doc-icon">📄</span>
          <div className="doc-info">
            <div className="doc-name">{doc.filename}</div>
            <div className="doc-meta">
              {doc.page_count}p · {doc.chunk_count} chunks · {formatBytes(doc.size_bytes)} · {formatDate(doc.uploaded_at)}
            </div>
          </div>
          <button
            className="doc-delete-btn"
            onClick={(e) => handleDelete(e, doc.id, doc.filename)}
            id={`delete-doc-${doc.id}`}
            title="Delete document"
          >
            <Trash2 size={13} />
          </button>
        </div>
      ))}
    </div>
  );
}
