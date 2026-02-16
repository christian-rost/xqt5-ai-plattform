import UsageWidget from './UsageWidget'
import AssistantSelector from './AssistantSelector'

export default function Sidebar({
  user,
  usage,
  conversations,
  activeId,
  loading,
  assistants,
  showAdmin,
  onCreateConversation,
  onOpenConversation,
  onDeleteConversation,
  onSelectAssistant,
  onManageAssistants,
  onManageTemplates,
  onAdmin,
  onLogout,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>XQT5 AI-Workplace</h1>
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

      <AssistantSelector assistants={assistants} onSelect={onSelectAssistant} />

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
              <button
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  if (confirm('Konversation löschen?')) onDeleteConversation(item.id)
                }}
                title="Konversation löschen"
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>

      <div className="sidebar-footer">
        {user?.is_admin && (
          <button
            className={`sidebar-admin-btn ${showAdmin ? 'active' : ''}`}
            onClick={onAdmin}
          >
            Admin-Dashboard
          </button>
        )}
        <div className="sidebar-actions">
          <button className="sidebar-action-btn" onClick={onManageAssistants}>Assistenten</button>
          <button className="sidebar-action-btn" onClick={onManageTemplates}>Templates</button>
        </div>
        <UsageWidget usage={usage} />
        <button className="logout-btn" onClick={onLogout}>Logout</button>
      </div>
    </aside>
  )
}
