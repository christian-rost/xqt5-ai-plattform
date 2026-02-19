import { useRef, useState } from 'react'
import { api } from '../api'

export default function PoolDocuments({ poolId, documents, canEdit, onUpload, onDelete }) {
  const fileInputRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState('')
  const [previewDoc, setPreviewDoc] = useState(null)

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

  async function handleOpenPreview(doc) {
    if (!poolId || !doc?.id) return
    setPreviewError('')
    setPreviewLoading(true)
    setPreviewDoc({
      filename: doc.filename,
      file_type: doc.file_type,
      text_preview: '',
      truncated: false,
      text_length: 0,
    })
    try {
      const preview = await api.getPoolDocumentPreview(poolId, doc.id)
      setPreviewDoc(preview)
    } catch (e) {
      setPreviewError(e.message || 'Vorschau konnte nicht geladen werden')
    } finally {
      setPreviewLoading(false)
    }
  }

  function closePreview() {
    setPreviewLoading(false)
    setPreviewError('')
    setPreviewDoc(null)
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
              <div className="pool-doc-actions">
                <button
                  className="btn btn-secondary btn-small pool-doc-preview"
                  onClick={() => handleOpenPreview(doc)}
                  title="Dokument-Vorschau öffnen"
                >
                  Vorschau
                </button>
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
            </div>
          ))}
        </div>
      )}

      {previewDoc && (
        <div className="pool-preview-modal-backdrop" onClick={closePreview}>
          <div className="pool-preview-modal" onClick={(e) => e.stopPropagation()}>
            <div className="pool-preview-header">
              <h3>Vorschau: {previewDoc.filename}</h3>
              <button className="pool-preview-close" onClick={closePreview} title="Schließen">
                &times;
              </button>
            </div>
            <div className="pool-preview-body">
              {previewLoading && <p>Lade Vorschau...</p>}
              {!previewLoading && previewError && <p className="pool-preview-error">{previewError}</p>}
              {!previewLoading && !previewError && (
                <>
                  {previewDoc.image_data_url && (
                    <img
                      src={previewDoc.image_data_url}
                      alt={previewDoc.filename || 'Bildvorschau'}
                      className="pool-preview-image"
                    />
                  )}
                  {previewDoc.text_preview ? (
                    <>
                      <pre className="pool-preview-text">{previewDoc.text_preview}</pre>
                      {previewDoc.truncated && (
                        <p className="pool-preview-hint">
                          Vorschau gekürzt ({previewDoc.text_length} Zeichen insgesamt).
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="pool-preview-empty">Keine Textvorschau verfügbar.</p>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
