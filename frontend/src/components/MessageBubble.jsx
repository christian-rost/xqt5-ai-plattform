import ReactMarkdown from 'react-markdown'
import SourceDisplay from './SourceDisplay'

export default function MessageBubble({ role, content, model, isStreaming, sources, imageSources, username }) {
  const displayContent = content || ''
  const isUser = role === 'user'

  return (
    <article className={`message ${role}${isStreaming ? ' streaming' : ''}`}>
      <div className="message-avatar">
        {isUser ? (username?.[0]?.toUpperCase() || 'D') : 'KI'}
      </div>

      <div className="message-body">
        <div className="message-bubble">
          <div className="message-content">
            {isUser ? (
              displayContent
            ) : (
              <ReactMarkdown>{displayContent}</ReactMarkdown>
            )}
            {isStreaming && <span className="streaming-cursor" />}
          </div>
        </div>

        <div className="message-meta">
          {isUser
            ? (username || 'Du')
            : model && <span className="message-model-tag">{model}</span>
          }
        </div>

        {!isUser && (
          <SourceDisplay sources={sources} imageSources={imageSources} />
        )}
      </div>
    </article>
  )
}
