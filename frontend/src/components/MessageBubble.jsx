import ReactMarkdown from 'react-markdown'

export default function MessageBubble({ role, content, model, isStreaming }) {
  const displayContent = content || ''

  return (
    <article className={`message ${role}${isStreaming ? ' streaming' : ''}`}>
      <div className="message-header">
        {role === 'user' ? 'YOU' : 'ASSISTANT'}
        {role === 'assistant' && model && (
          <span className="message-model">{model}</span>
        )}
      </div>
      <div className="message-content">
        {role === 'assistant' ? (
          <ReactMarkdown>{displayContent}</ReactMarkdown>
        ) : (
          displayContent
        )}
        {isStreaming && <span className="streaming-cursor" />}
      </div>
    </article>
  )
}
