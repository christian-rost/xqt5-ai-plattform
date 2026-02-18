import { useRef, useState } from 'react'

export default function PoolDocuments({ documents, canEdit, onUpload, onDelete }) {
  const fileInputRef = useRef(null)
  const [uploading, setUploading] = useState(false)

  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await onUpload(file)
    } catch {
      // Error handled by parent
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="pool-documents">
      {canEdit && (
        <div className="pool-documents-upload">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.png,.jpg,.jpeg,.webp"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <button
            className="btn btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? 'Lade hoch...' : 'Dokument hochladen'}
          </button>
          <span className="pool-upload-hint">PDF, TXT oder Bild</span>
        </div>
      )}

      {documents.length === 0 ? (
        <div className="pool-empty-state">
          Noch keine Dokumente vorhanden.
          {canEdit && ' Lade ein Dokument hoch, um loszulegen.'}
        </div>
      ) : (
        <div className="pool-document-list">
          {documents.map((doc) => (
            <div key={doc.id} className={`pool-doc-item doc-status-${doc.status}`}>
              <span className="pool-doc-icon">
                {doc.file_type === 'pdf' ? '\u{1F4C4}' : (doc.file_type === 'image' ? '\u{1F5BC}\u{FE0F}' : '\u{1F4DD}')}
              </span>
              <div className="pool-doc-info">
                <span className="pool-doc-name">{doc.filename}</span>
                <span className="pool-doc-meta">
                  {doc.status === 'ready' && `${doc.chunk_count} Chunks`}
                  {doc.status === 'processing' && 'Verarbeitung...'}
                  {doc.status === 'error' && (doc.error_message || 'Fehler')}
                  {' \u00B7 '}
                  {(doc.file_size_bytes / 1024).toFixed(0)} KB
                </span>
              </div>
              {canEdit && (
                <button
                  className="pool-doc-delete"
                  onClick={() => {
                    if (confirm('Dokument löschen?')) onDelete(doc.id)
                  }}
                  title="Dokument löschen"
                >
                  &times;
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
