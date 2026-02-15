export default function ModelSelector({ models, selectedModel, onChange }) {
  return (
    <div className="model-selector">
      <select
        value={selectedModel}
        onChange={(e) => onChange(e.target.value)}
        className="model-select"
      >
        {models.map((m) => (
          <option key={m.id} value={m.id} disabled={!m.available}>
            {m.name} {!m.available ? '(no key)' : ''}
          </option>
        ))}
      </select>
    </div>
  )
}
