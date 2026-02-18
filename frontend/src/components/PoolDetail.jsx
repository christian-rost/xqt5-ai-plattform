import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import PoolDocuments from './PoolDocuments'
import PoolChatList from './PoolChatList'
import PoolChatArea from './PoolChatArea'
import PoolMembers from './PoolMembers'

export default function PoolDetail({
  pool,
  models,
  selectedModel,
  defaultModelId,
  user,
  onClose,
  onPoolUpdated,
  onError,
}) {
  const [activeTab, setActiveTab] = useState('documents')
  const [activeChat, setActiveChat] = useState(null)
  const [chats, setChats] = useState([])
  const [documents, setDocuments] = useState([])
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState(null)
  const [chatModel, setChatModel] = useState(selectedModel)
  const [chatImageMode, setChatImageMode] = useState('auto')
  const [error, setError] = useState('')

  const role = pool.role || 'viewer'
  const canEdit = role === 'editor' || role === 'admin' || role === 'owner'
  const canAdmin = role === 'admin' || role === 'owner'
  const isOwner = role === 'owner'

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await api.listPoolDocuments(pool.id)
      setDocuments(docs)
    } catch {}
  }, [pool.id])

  const loadChats = useCallback(async () => {
    try {
      const data = await api.listPoolChats(pool.id)
      setChats(data)
    } catch {}
  }, [pool.id])

  const loadMembers = useCallback(async () => {
    try {
      const data = await api.listPoolMembers(pool.id)
      setMembers(data)
    } catch {}
  }, [pool.id])

  useEffect(() => {
    loadDocuments()
    loadChats()
    loadMembers()
  }, [loadDocuments, loadChats, loadMembers])

  async function handleUploadDocument(file) {
    setError('')
    try {
      await api.uploadPoolDocument(pool.id, file)
      await loadDocuments()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDeleteDocument(docId) {
    setError('')
    try {
      await api.deletePoolDocument(pool.id, docId)
      await loadDocuments()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleCreateChat(isShared) {
    setError('')
    try {
      const chat = await api.createPoolChat(pool.id, {
        title: 'New Chat',
        is_shared: isShared,
        model: chatModel,
      })
      await loadChats()
      await handleOpenChat(chat.id)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleOpenChat(chatId) {
    setError('')
    setLoading(true)
    try {
      const chat = await api.getPoolChat(pool.id, chatId)
      setActiveChat(chat)
      setChatModel(chat.model || selectedModel)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteChat(chatId) {
    setError('')
    try {
      await api.deletePoolChat(pool.id, chatId)
      if (activeChat?.id === chatId) setActiveChat(null)
      await loadChats()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleSendMessage(content) {
    if (!activeChat) return
    setError('')

    const optimisticMessages = [
      ...(activeChat.messages || []),
      { role: 'user', content, username: user.username },
    ]
    setActiveChat((prev) => ({ ...prev, messages: optimisticMessages }))
    setLoading(true)
    setStreamingContent('')

    try {
      await api.sendPoolMessageStream(
        pool.id,
        activeChat.id,
        content,
        chatModel,
        null,
        chatImageMode,
        (delta) => {
          setStreamingContent((prev) => (prev || '') + delta)
        },
        async (fullContent, sources, imageSources) => {
          setStreamingContent(null)
          setLoading(false)
          const updated = await api.getPoolChat(pool.id, activeChat.id)
          if (updated.messages) {
            const lastMsg = updated.messages[updated.messages.length - 1]
            if (lastMsg && lastMsg.role === 'assistant') {
              if (sources && sources.length > 0) {
                lastMsg.sources = sources
              }
              if (imageSources && imageSources.length > 0) {
                lastMsg.image_sources = imageSources
              }
            }
          }
          setActiveChat(updated)
          await loadChats()
        },
        (err) => {
          setStreamingContent(null)
          setLoading(false)
          setError(err)
        }
      )
    } catch (e) {
      setStreamingContent(null)
      setLoading(false)
      setError(e.message)
    }
  }

  async function handleDeletePool() {
    if (!confirm('Pool wirklich löschen? Alle Dokumente und Chats werden gelöscht.')) return
    try {
      await api.deletePool(pool.id)
      onClose()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleLeavePool() {
    if (!confirm('Pool wirklich verlassen?')) return
    try {
      await api.removePoolMember(pool.id, user.id)
      onClose()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <main className="pool-detail">
      <div className="pool-detail-header">
        <div className="pool-detail-title">
          <span className="pool-detail-icon" style={{ color: pool.color }}>
            {pool.icon || '\u{1F4DA}'}
          </span>
          <div>
            <h2>{pool.name}</h2>
            {pool.description && <p className="pool-detail-desc">{pool.description}</p>}
          </div>
        </div>
        <div className="pool-detail-actions">
          {!isOwner && (
            <button className="btn btn-secondary btn-small" onClick={handleLeavePool}>
              Verlassen
            </button>
          )}
          {isOwner && (
            <button className="btn btn-danger btn-small" onClick={handleDeletePool}>
              Löschen
            </button>
          )}
          <button className="btn btn-secondary btn-small" onClick={onClose}>
            Schließen
          </button>
        </div>
      </div>

      {error && <p className="error-banner">{error}</p>}

      <div className="pool-tabs">
        <button
          className={`pool-tab ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => { setActiveTab('documents'); setActiveChat(null) }}
        >
          Dokumente ({documents.length})
        </button>
        <button
          className={`pool-tab ${activeTab === 'chats' ? 'active' : ''}`}
          onClick={() => setActiveTab('chats')}
        >
          Chats ({chats.length})
        </button>
        <button
          className={`pool-tab ${activeTab === 'members' ? 'active' : ''}`}
          onClick={() => { setActiveTab('members'); setActiveChat(null) }}
        >
          Mitglieder ({members.length})
        </button>
      </div>

      <div className="pool-content">
        {activeTab === 'documents' && (
          <PoolDocuments
            documents={documents}
            canEdit={canEdit}
            onUpload={handleUploadDocument}
            onDelete={handleDeleteDocument}
          />
        )}

        {activeTab === 'chats' && !activeChat && (
          <PoolChatList
            chats={chats}
            userId={user.id}
            onOpenChat={handleOpenChat}
            onCreateChat={handleCreateChat}
            onDeleteChat={handleDeleteChat}
          />
        )}

        {activeTab === 'chats' && activeChat && (
          <PoolChatArea
            chat={activeChat}
            models={models}
            selectedModel={chatModel}
            imageMode={chatImageMode}
            loading={loading}
            streamingContent={streamingContent}
            onSend={handleSendMessage}
            onModelChange={setChatModel}
            onImageModeChange={setChatImageMode}
            onBack={() => setActiveChat(null)}
          />
        )}

        {activeTab === 'members' && (
          <PoolMembers
            poolId={pool.id}
            members={members}
            canAdmin={canAdmin}
            isOwner={isOwner}
            currentUserId={user.id}
            onMembersChanged={loadMembers}
          />
        )}
      </div>
    </main>
  )
}
