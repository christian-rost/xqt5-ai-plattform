import { useEffect, useState } from 'react'
import { api } from './api'

export default function App() {
  const [conversations, setConversations] = useState([])
  const [activeConversation, setActiveConversation] = useState(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function loadConversations() {
    try {
      const data = await api.listConversations()
      setConversations(data)
      if (!activeConversation && data.length > 0) {
        const full = await api.getConversation(data[0].id)
        setActiveConversation(full)
      }
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    loadConversations()
  }, [])

  async function onCreateConversation() {
    setLoading(true)
    setError('')
    try {
      const created = await api.createConversation('Neue Konversation')
      setConversations((prev) => [
        {
          id: created.id,
          created_at: created.created_at,
          title: created.title,
          message_count: 0,
        },
        ...prev,
      ])
      setActiveConversation(created)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function onOpenConversation(id) {
    setLoading(true)
    setError('')
    try {
      const full = await api.getConversation(id)
      setActiveConversation(full)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function onSendMessage(event) {
    event.preventDefault()
    if (!activeConversation || !message.trim()) return

    setLoading(true)
    setError('')
    try {
      const updated = await api.sendMessage(activeConversation.id, message.trim())
      setActiveConversation(updated)
      setMessage('')
      await loadConversations()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>XQT5 AI</h1>
        <button className="primary" onClick={onCreateConversation} disabled={loading}>
          Neue Konversation
        </button>
        <ul>
          {conversations.map((item) => (
            <li key={item.id}>
              <button onClick={() => onOpenConversation(item.id)}>{item.title}</button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="content">
        <header>
          <h2>{activeConversation?.title || 'Keine Konversation ausgewählt'}</h2>
        </header>

        {error && <p className="error">{error}</p>}

        <section className="messages">
          {(activeConversation?.messages || []).map((m, index) => (
            <article key={index} className={`bubble ${m.role}`}>
              <strong>{m.role === 'user' ? 'Du' : 'Assistant'}:</strong>
              <p>{m.content || m.stage3?.answer || ''}</p>
            </article>
          ))}
        </section>

        <form className="composer" onSubmit={onSendMessage}>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Nachricht eingeben..."
            disabled={loading || !activeConversation}
          />
          <button className="primary" type="submit" disabled={loading || !activeConversation}>
            Senden
          </button>
        </form>
      </main>
    </div>
  )
}
