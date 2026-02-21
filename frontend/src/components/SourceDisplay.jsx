import { useState } from 'react'

export default function SourceDisplay({ sources, imageSources }) {
  const [expanded, setExpanded] = useState({})

  const unique = []
  const seen = new Set()
  for (const s of (sources || [])) {
    const key = s.filename || 'unknown'
    if (!seen.has(key)) {
      seen.add(key)
      unique.push(s)
    }
  }

  const hasText = unique.length > 0
  const hasImages = (imageSources || []).length > 0
  if (!hasText && !hasImages) return null

  const toggle = (fn) => setExpanded(p => ({ ...p, [fn]: !p[fn] }))

  return (
    <>
      {hasText && (
        <div className="rag-sources">
          <span className="rag-sources-label">Sources:</span>
          <div className="rag-source-list">
            {unique.map((s, i) => {
              const fn = s.filename || 'unknown'
              const isOpen = expanded[fn]
              return (
                <div key={i} className="rag-source-item">
                  <button
                    className={`source-tag${s.excerpt ? ' source-tag--citable' : ''}${isOpen ? ' source-tag--open' : ''}`}
                    onClick={() => s.excerpt && toggle(fn)}
                    title={`Relevanz: ${Math.round((s.similarity || 0) * 100)}%`}
                  >
                    {fn}
                    {s.excerpt && (
                      <span className="source-tag-chevron">{isOpen ? '▲' : '▼'}</span>
                    )}
                  </button>
                  {s.excerpt && isOpen && (
                    <blockquote className="source-excerpt">„{s.excerpt}"</blockquote>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {hasImages && (
        <div className="rag-image-sources">
          <span className="rag-sources-label">Image Sources:</span>
          <div className="rag-image-grid">
            {imageSources.map((img, i) => (
              <figure key={img.asset_id || i} className="rag-image-item">
                {img.url ? (
                  <img
                    src={img.url}
                    alt={img.caption || img.filename || 'Image source'}
                    loading="lazy"
                  />
                ) : null}
                <figcaption>
                  <strong>{img.filename || 'document'}</strong>
                  {img.page_number != null ? ` (p. ${img.page_number})` : ''}
                  {img.caption ? ` - ${img.caption}` : ''}
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
