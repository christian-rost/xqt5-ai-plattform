export default function SourceDisplay({ sources }) {
  if (!sources || sources.length === 0) return null

  // Deduplicate by filename
  const unique = []
  const seen = new Set()
  for (const s of sources) {
    if (!seen.has(s.filename)) {
      seen.add(s.filename)
      unique.push(s)
    }
  }

  return (
    <div className="rag-sources">
      <span className="rag-sources-label">Sources:</span>
      {unique.map((s, i) => (
        <span key={i} className="source-tag" title={`Relevance: ${Math.round(s.similarity * 100)}%`}>
          {s.filename}
        </span>
      ))}
    </div>
  )
}
