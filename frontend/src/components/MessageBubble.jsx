import ReactMarkdown from 'react-markdown'
import SourceDisplay from './SourceDisplay'

export default function MessageBubble({ role, content, model, isStreaming, sources }) {
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
      {role === 'assistant' && sources && sources.length > 0 && (
        <SourceDisplay sources={sources} />
      )}
    </article>
  )
}
