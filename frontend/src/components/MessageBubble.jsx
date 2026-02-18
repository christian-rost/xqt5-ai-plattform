import ReactMarkdown from 'react-markdown'
import SourceDisplay from './SourceDisplay'

export default function MessageBubble({ role, content, model, isStreaming, sources, imageSources, username }) {
  const displayContent = content || ''

  return (
    <article className={`message ${role}${isStreaming ? ' streaming' : ''}`}>
      <div className="message-header">
        {role === 'user' ? (username || 'YOU') : 'ASSISTANT'}
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
      {role === 'assistant' && (
        <SourceDisplay sources={sources} imageSources={imageSources} />
      )}
    </article>
  )
}
