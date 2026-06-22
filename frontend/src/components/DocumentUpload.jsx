import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadDocument } from '../services/api';

export default function DocumentUpload({ onUploaded, onToast }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [filename, setFilename] = useState('');
  const [status, setStatus] = useState('');

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setFilename(file.name);
    setUploading(true);
    setProgress(0);
    setStatus('Uploading...');

    try {
      const doc = await uploadDocument(file, (pct) => {
        setProgress(pct);
        if (pct === 100) setStatus('Processing with AI (this may take a minute)...');
      });
      onToast('success', `✅ "${doc.filename}" indexed — ${doc.chunk_count} chunks ready`);
      onUploaded(doc);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      onToast('error', `❌ Upload failed: ${msg}`);
    } finally {
      setUploading(false);
      setProgress(0);
      setFilename('');
      setStatus('');
    }
  }, [onUploaded, onToast]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: uploading,
  });

  if (uploading) {
    return (
      <div className="upload-progress">
        <div className="progress-filename">📄 {filename}</div>
        <div className="progress-bar-track">
          <div
            className="progress-bar-fill"
            style={{ width: `${progress === 100 ? 100 : Math.max(progress, 5)}%` }}
          />
        </div>
        <div className="progress-status">{status}</div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`upload-zone ${isDragActive ? 'drag-active' : ''}`}
      id="upload-zone"
    >
      <input {...getInputProps()} id="pdf-upload-input" />
      <span className="upload-icon">📎</span>
      <div className="upload-title">
        {isDragActive ? 'Drop the PDF here' : 'Upload a PDF'}
      </div>
      <div className="upload-subtitle">Drag & drop or click to browse</div>
      <div className="upload-hint">PDF files only</div>
    </div>
  );
}
