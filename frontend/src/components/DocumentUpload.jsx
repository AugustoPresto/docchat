import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadDocument } from '../services/api';

export default function DocumentUpload({ onUploaded, onToast, maxMb }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [filename, setFilename] = useState('');

  const onDrop = useCallback(async (acceptedFiles, rejected) => {
    if (rejected?.length) {
      onToast('error', '❌ Only PDF files are supported.');
      return;
    }
    const file = acceptedFiles[0];
    if (!file) return;

    if (maxMb && file.size > maxMb * 1024 * 1024) {
      onToast('error', `❌ "${file.name}" is larger than ${maxMb} MB.`);
      return;
    }

    setFilename(file.name);
    setUploading(true);
    setProgress(0);

    try {
      // The server answers as soon as the file is saved; indexing progress
      // is then shown in the document list.
      const doc = await uploadDocument(file, setProgress);
      onUploaded(doc);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      onToast('error', `❌ Upload failed: ${msg}`);
    } finally {
      setUploading(false);
      setProgress(0);
      setFilename('');
    }
  }, [onUploaded, onToast, maxMb]);

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
          <div className="progress-bar-fill" style={{ width: `${Math.max(progress, 5)}%` }} />
        </div>
        <div className="progress-status">Uploading… {progress}%</div>
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
      <div className="upload-hint">
        PDF files only{maxMb ? ` (max ${maxMb}MB)` : ''}
      </div>
    </div>
  );
}
