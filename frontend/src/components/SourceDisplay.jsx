export default function SourceDisplay({ sources, imageSources }) {
  const hasTextSources = sources && sources.length > 0
  const hasImageSources = imageSources && imageSources.length > 0
  if (!hasTextSources && !hasImageSources) return null

  // Deduplicate by filename
  const unique = []
  const seen = new Set()
  for (const s of (sources || [])) {
    const key = s.filename || 'unknown'
    if (!seen.has(key)) {
      seen.add(key)
      unique.push(s)
    }
  }

  return (
    <>
      {hasTextSources && (
        <div className="rag-sources">
          <span className="rag-sources-label">Sources:</span>
          {unique.map((s, i) => (
            <span key={i} className="source-tag" title={`Relevance: ${Math.round((s.similarity || 0) * 100)}%`}>
              {s.filename || 'unknown'}
            </span>
          ))}
        </div>
      )}

      {hasImageSources && (
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
