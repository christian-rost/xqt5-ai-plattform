export default function Sidebar({
  conversations,
  activeId,
  loading,
  onCreateConversation,
  onOpenConversation,
}) {
  return (
    <aside className="sidebar">
      <h1>XQT5 AI</h1>
      <button
        className="new-chat-btn"
        onClick={onCreateConversation}
        disabled={loading}
      >
        New Conversation
      </button>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((item) => (
            <div
              key={item.id}
              className={`conversation-item ${activeId === item.id ? 'active' : ''}`}
              onClick={() => onOpenConversation(item.id)}
            >
              <span className="conversation-title">{item.title}</span>
              <span className="message-count">{item.message_count} messages</span>
            </div>
          ))
        )}
      </div>
    </aside>
  )
}
