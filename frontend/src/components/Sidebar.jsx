import { useEffect, useState } from 'react';
import DocumentUpload from './DocumentUpload';
import DocumentList from './DocumentList';
import { checkHealth } from '../services/api';
import { X } from 'lucide-react';

function DeviceBadge({ device, gpuName, vramGb }) {
  const isGpu = device === 'cuda' || device === 'mps';
  const label = device === 'cuda'
    ? `GPU · ${gpuName || 'NVIDIA'}${vramGb ? ` · ${vramGb}GB` : ''}`
    : device === 'mps'
    ? 'Apple Silicon'
    : 'CPU only';

  const tooltipText = isGpu
    ? "Embeddings are accelerated using hardware GPU."
    : "For cost-efficiency in cloud hosting, this application processes document embeddings using CPU cores. Processing very large PDFs may take longer.";

  return (
    <span
      title={tooltipText}
      style={{
        fontSize: '10px',
        fontWeight: 600,
        padding: '2px 7px',
        borderRadius: '999px',
        background: isGpu ? 'rgba(34,197,94,0.12)' : 'rgba(245,158,11,0.12)',
        border: `1px solid ${isGpu ? 'rgba(34,197,94,0.4)' : 'rgba(245,158,11,0.4)'}`,
        color: isGpu ? '#22c55e' : '#f59e0b',
        letterSpacing: '0.3px',
        cursor: isGpu ? 'default' : 'help',
      }}
    >
      {isGpu ? '⚡' : '🖥️'} {label}
    </span>
  );
}

export default function Sidebar({ documents, activeDocId, onUploaded, onSelect, onDeleted, onToast, health, healthStatus, isOpen, onClose }) {
  const isCloud = health?.provider === 'groq' || health?.provider === 'openai';
  const logoTagline = isCloud
    ? `Powered by ${health.provider.toUpperCase()} (Cloud LLM)`
    : 'Powered by Ollama · 100% local';

  const statusLabel = healthStatus === 'loading'
    ? 'Connecting…'
    : healthStatus === 'error'
    ? 'AI offline'
    : health?.provider === 'groq'
    ? 'Groq connected'
    : health?.provider === 'openai'
    ? 'OpenAI connected'
    : 'Ollama connected';

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      {/* Logo */}
      <div className="sidebar-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
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
        <DocumentUpload onUploaded={onUploaded} onToast={onToast} isCloud={isCloud} />

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
