import { useState, useRef, useEffect } from 'react'

export default function TemplatePicker({ templates, onSelect }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  if (!templates || templates.length === 0) return null

  return (
    <div className="template-picker" ref={ref}>
      <button
        className="template-picker-btn"
        onClick={() => setOpen(!open)}
        title="Template einfügen"
        type="button"
      >
        Templates
      </button>
      {open && (
        <div className="template-picker-dropdown">
          {templates.map((t) => (
            <button
              key={t.id}
              className="template-picker-item"
              onClick={() => {
                onSelect(t.content)
                setOpen(false)
              }}
            >
              <span className="template-picker-name">{t.name}</span>
              <span className="template-picker-cat">{t.category}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
