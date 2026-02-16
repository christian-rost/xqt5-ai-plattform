export default function AssistantSelector({ assistants, onSelect }) {
  if (!assistants || assistants.length === 0) return null

  return (
    <div className="assistant-selector">
      <div className="assistant-selector-label">Assistenten</div>
      <div className="assistant-grid">
        {assistants.map((a) => (
          <button
            key={a.id}
            className="assistant-card"
            onClick={() => onSelect(a)}
            title={a.description || a.name}
          >
            <span className="assistant-icon">{a.icon || '\u{1F916}'}</span>
            <span className="assistant-name">{a.name}</span>
            {a.is_global && <span className="assistant-global-badge">Global</span>}
          </button>
        ))}
      </div>
    </div>
  )
}
