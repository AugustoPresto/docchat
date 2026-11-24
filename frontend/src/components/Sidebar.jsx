import DocumentUpload from './DocumentUpload';
import DocumentList from './DocumentList';
import { X } from 'lucide-react';

function DeviceBadge({ device, gpuName, vramGb }) {
  const isGpu = device === 'cuda' || device === 'mps';
  const label = device === 'cuda'
    ? `GPU · ${gpuName || 'NVIDIA'}${vramGb ? ` · ${vramGb}GB` : ''}`
    : device === 'mps'
    ? 'Apple Silicon'
    : 'CPU only';

  const tooltipText = isGpu
    ? 'Embeddings are accelerated using hardware GPU.'
    : 'Embeddings run on the CPU with a lightweight ONNX model, so DocChat works on machines without a GPU. Very large PDFs take longer.';

  return (
    <span title={tooltipText} className={`device-badge ${isGpu ? 'gpu' : 'cpu'}`}>
      {isGpu ? '⚡' : '🖥️'} {label}
    </span>
  );
}

export default function Sidebar({ documents, activeDocId, onUploaded, onSelect, onDeleted, onToast, health, healthStatus, slowStart, isOpen, onClose }) {
  const isCloud = health?.provider === 'groq' || health?.provider === 'openai';
  const logoTagline = !health
    ? 'Chat with your PDFs'
    : isCloud
    ? `Powered by ${health.provider.toUpperCase()} (Cloud LLM)`
    : 'Powered by Ollama · 100% local';

  const statusLabel = healthStatus === 'loading'
    ? (slowStart ? 'Waking up server (up to 1 min)…' : 'Connecting…')
    : healthStatus === 'error'
    ? 'Server offline — retrying…'
    : health?.provider === 'groq'
    ? 'Groq connected'
    : health?.provider === 'openai'
    ? 'OpenAI connected'
    : 'Ollama connected';

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      {/* Logo */}
      <div className="sidebar-header">
        <div className="sidebar-header-row">
          <div className="logo">
            <div className="logo-icon">💬</div>
            <span className="logo-text">DocChat</span>
          </div>
          <button className="sidebar-close-btn" onClick={onClose} aria-label="Close sidebar">
            <X size={18} />
          </button>
        </div>
        <div className="logo-tagline">{logoTagline}</div>
      </div>

      {/* Upload + Documents */}
      <div className="sidebar-section">
        <div className="section-label">Upload</div>
        <DocumentUpload onUploaded={onUploaded} onToast={onToast} maxMb={health?.max_upload_mb} />

        <div className="section-label section-label-spaced">
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

      {/* Status bar */}
      <div className="status-bar">
        <div className={`status-dot ${healthStatus}`} />
        <span className="status-text">
          {statusLabel}
        </span>
        {health && (
          <DeviceBadge
            device={health.device}
            gpuName={health.gpu_name}
            vramGb={health.vram_gb}
          />
        )}
      </div>
    </aside>
  );
}
