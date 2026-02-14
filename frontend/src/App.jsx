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

      if (activeConversation) {
        const refreshed = data.find((item) => item.id === activeConversation.id)
        if (!refreshed) {
          setActiveConversation(null)
        }
      }

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
      const created = await api.createConversation('New Conversation')
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
    <div className="app">
      <aside className="sidebar">
        <h1>XQT5 AI</h1>
        <button className="new-chat-btn" onClick={onCreateConversation} disabled={loading}>
          New Conversation
        </button>

        <div className="conversation-list">
          {conversations.length === 0 ? (
            <div className="no-conversations">No conversations yet</div>
          ) : (
            conversations.map((item) => (
              <div
                key={item.id}
                className={`conversation-item ${activeConversation?.id === item.id ? 'active' : ''}`}
                onClick={() => onOpenConversation(item.id)}
              >
                <span className="conversation-title">{item.title}</span>
                <span className="message-count">{item.message_count} messages</span>
              </div>
            ))
          )}
        </div>
      </aside>

      <main className="chat-area">
        {error && <p className="error-banner">{error}</p>}

        {!activeConversation ? (
          <div className="welcome">
            <h2>Welcome to XQT5 AI</h2>
            <p>Create a new conversation to get started.</p>
          </div>
        ) : (
          <>
            <section className="messages">
              {(activeConversation.messages || []).map((m, index) => (
                <article key={index} className={`message ${m.role}`}>
                  <div className="message-header">{m.role === 'user' ? 'USER' : 'ASSISTANT'}</div>
                  <div className="message-content">{m.content || m.stage3?.answer || ''}</div>
                </article>
              ))}
            </section>

            <form className="input-form" onSubmit={onSendMessage}>
              <textarea
                className="message-input"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Type your message..."
                disabled={loading}
              />
              <button
                className="send-button"
                type="submit"
                disabled={loading || !message.trim()}
              >
                Send
              </button>
            </form>
          </>
        )}
      </main>
    </div>
  )
}
