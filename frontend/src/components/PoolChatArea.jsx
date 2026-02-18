import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble'

export default function PoolChatArea({
  chat,
  models,
  selectedModel,
  imageMode,
  loading,
  streamingContent,
  onSend,
  onModelChange,
  onImageModeChange,
  onBack,
}) {
  const messagesEndRef = useRef(null)
  const [input, setInput] = useState('')

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat?.messages, streamingContent])

  function handleSubmit(e) {
    e.preventDefault()
    if (!input.trim() || loading) return
    onSend(input.trim())
    setInput('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="pool-chat-area">
      <div className="pool-chat-header">
        <button className="btn btn-secondary btn-small" onClick={onBack}>
          &larr; Zurück
        </button>
        <span className="pool-chat-title">
          {chat.is_shared ? '\u{1F30D}' : '\u{1F512}'} {chat.title}
        </span>
        <select
          className="model-select"
          value={selectedModel}
          onChange={(e) => onModelChange(e.target.value)}
        >
          {(models || []).map((m) => (
            <option key={m.id} value={m.id} disabled={!m.available}>
              {m.display_name || m.name || m.id}
            </option>
          ))}
        </select>
        <select
          className="model-select"
          value={imageMode || 'auto'}
          onChange={(e) => onImageModeChange?.(e.target.value)}
        >
          <option value="auto">Bildquellen: Auto</option>
          <option value="on">Bildquellen: Ein</option>
          <option value="off">Bildquellen: Aus</option>
        </select>
      </div>

      <section className="messages pool-messages">
        {(chat.messages || []).map((m, index) => (
          <MessageBubble
            key={index}
            role={m.role}
            content={m.content || ''}
            model={m.model}
            sources={m.sources}
            imageSources={m.image_sources}
            username={m.username}
          />
        ))}

        {streamingContent !== null && (
          <MessageBubble
            role="assistant"
            content={streamingContent}
            isStreaming={true}
          />
        )}

        <div ref={messagesEndRef} />
      </section>

      <form className="pool-chat-input" onSubmit={handleSubmit}>
        <textarea
          className="message-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nachricht eingeben..."
          disabled={loading}
          rows={2}
        />
        <button
          className="send-button"
          type="submit"
          disabled={!input.trim() || loading}
        >
          {loading ? '...' : 'Senden'}
        </button>
      </form>
    </div>
  )
}
