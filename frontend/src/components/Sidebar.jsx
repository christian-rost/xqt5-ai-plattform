import UsageWidget from './UsageWidget'

export default function Sidebar({
  user,
  usage,
  conversations,
  activeId,
  loading,
  onCreateConversation,
  onOpenConversation,
  onLogout,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>XQT5 AI</h1>
        <div className="user-info">
          <span className="user-name">{user?.username}</span>
          {user?.is_admin && <span className="admin-badge">Admin</span>}
        </div>
      </div>

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

      <div className="sidebar-footer">
        <UsageWidget usage={usage} />
        <button className="logout-btn" onClick={onLogout}>Logout</button>
      </div>
    </aside>
  )
}
