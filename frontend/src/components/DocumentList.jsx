export default function DocumentList({ documents, onDelete }) {
  if (!documents || documents.length === 0) return null

  return (
    <div className="document-list">
      {documents.map((doc) => (
        <span
          key={doc.id}
          className={`document-item doc-status-${doc.status}`}
          title={doc.error_message || `${doc.chunk_count} chunks`}
        >
          <span className="doc-icon">
            {doc.file_type === 'pdf' ? '\u{1F4C4}' : (doc.file_type === 'image' ? '\u{1F5BC}\u{FE0F}' : '\u{1F4DD}')}
          </span>
          <span className="doc-name">{doc.filename}</span>
          {doc.status === 'ready' && (
            <span className="doc-chunks">{doc.chunk_count}</span>
          )}
          {doc.status === 'processing' && (
            <span className="doc-processing">...</span>
          )}
          {doc.status === 'error' && (
            <span className="doc-error-icon" title={doc.error_message}>!</span>
          )}
          <button
            className="doc-delete"
            onClick={() => onDelete(doc.id)}
            title="Remove document"
          >
            &times;
          </button>
        </span>
      ))}
    </div>
  )
}
