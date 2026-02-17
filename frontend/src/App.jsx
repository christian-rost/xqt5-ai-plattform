import { useEffect, useState, useCallback } from 'react'
import { api } from './api'
import LoginScreen from './components/LoginScreen'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import AdminDashboard from './components/AdminDashboard'
import AssistantManager from './components/AssistantManager'
import TemplateManager from './components/TemplateManager'

const DEFAULT_MODEL = 'google/gemini-3-pro-preview'
const DEFAULT_TEMPERATURE = 0.7

export default function App() {
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [usage, setUsage] = useState(null)

  const [conversations, setConversations] = useState([])
  const [activeConversation, setActiveConversation] = useState(null)
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL)
  const [temperature, setTemperature] = useState(DEFAULT_TEMPERATURE)
  const [loading, setLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState(null)
  const [error, setError] = useState('')

  // Phase C state
  const [assistants, setAssistants] = useState([])
  const [templates, setTemplates] = useState([])
  const [showAssistantManager, setShowAssistantManager] = useState(false)
  const [showTemplateManager, setShowTemplateManager] = useState(false)

  // Phase C Step 2: Documents / RAG
  const [chatDocuments, setChatDocuments] = useState([])

  // Phase D state
  const [showAdmin, setShowAdmin] = useState(false)

  // Check auth on mount
  useEffect(() => {
    api.getMe().then((u) => {
      setUser(u)
      setAuthChecked(true)
    }).catch(() => setAuthChecked(true))
  }, [])

  // Load models (public endpoint)
  useEffect(() => {
    api.listModels().then((data) => {
      setModels(data)
      const firstAvailable = data.find((m) => m.available)
      if (firstAvailable) setSelectedModel(firstAvailable.id)
    }).catch(() => {})
  }, [])

  const loadUsage = useCallback(async () => {
    if (!user) return
    try {
      const data = await api.getUsage()
      setUsage(data)
    } catch {}
  }, [user])

  // Load usage after login
  useEffect(() => {
    if (user) loadUsage()
  }, [user, loadUsage])

  const loadConversations = useCallback(async () => {
    if (!user) return
    try {
      const data = await api.listConversations()
      setConversations(data)
    } catch (e) {
      setError(e.message)
    }
  }, [user])

  useEffect(() => {
    if (user) loadConversations()
  }, [user, loadConversations])

  // Load assistants and templates
  const loadAssistants = useCallback(async () => {
    if (!user) return
    try {
      const data = await api.listAssistants()
      setAssistants(data)
    } catch {}
  }, [user])

  const loadTemplates = useCallback(async () => {
    if (!user) return
    try {
      const data = await api.listTemplates()
      setTemplates(data)
    } catch {}
  }, [user])

  useEffect(() => {
    if (user) {
      loadAssistants()
      loadTemplates()
    }
  }, [user, loadAssistants, loadTemplates])

  // Sync model/temperature when conversation changes
  useEffect(() => {
    if (activeConversation) {
      if (activeConversation.model) setSelectedModel(activeConversation.model)
      if (activeConversation.temperature != null) setTemperature(activeConversation.temperature)
    }
  }, [activeConversation?.id])

  // Load documents for active conversation
  const loadDocuments = useCallback(async () => {
    if (!activeConversation?.id) {
      setChatDocuments([])
      return
    }
    try {
      const docs = await api.listDocuments(activeConversation.id, 'all')
      setChatDocuments(docs)
    } catch {}
  }, [activeConversation?.id])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  async function handleAuth(mode, { username, email, password }) {
    if (mode === 'register') {
      const u = await api.register(username, email, password)
      setUser(u)
    } else {
      const u = await api.login(username, password)
      setUser(u)
    }
  }

  function handleLogout() {
    api.logout()
    setUser(null)
    setConversations([])
    setActiveConversation(null)
    setUsage(null)
    setAssistants([])
    setTemplates([])
  }

  async function onCreateConversation(assistantId = null) {
    setLoading(true)
    setError('')
    try {
      const created = await api.createConversation('New Conversation', assistantId)
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

  async function onSelectAssistant(assistant) {
    await onCreateConversation(assistant.id)
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

  async function onDeleteConversation(id) {
    setError('')
    try {
      await api.deleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeConversation?.id === id) {
        setActiveConversation(null)
      }
    } catch (e) {
      setError(e.message)
    }
  }

  async function onSendMessage(content) {
    if (!activeConversation) return

    setError('')

    // Optimistic: show user message immediately
    const optimisticMessages = [
      ...(activeConversation.messages || []),
      { role: 'user', content },
    ]
    setActiveConversation((prev) => ({ ...prev, messages: optimisticMessages }))
    setLoading(true)
    setStreamingContent('')

    try {
      await api.sendMessageStream(
        activeConversation.id,
        content,
        selectedModel,
        temperature,
        (delta) => {
          setStreamingContent((prev) => (prev || '') + delta)
        },
        async (fullContent, sources) => {
          // Stream complete — finalize
          setStreamingContent(null)
          setLoading(false)

          // Refresh conversation to get stored messages
          const updated = await api.getConversation(activeConversation.id)
          // Attach RAG sources to the last assistant message
          if (sources && sources.length > 0 && updated.messages) {
            const lastMsg = updated.messages[updated.messages.length - 1]
            if (lastMsg && lastMsg.role === 'assistant') {
              lastMsg.sources = sources
            }
          }
          setActiveConversation(updated)
          await loadConversations()
          await loadUsage()
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

  async function onModelChange(model) {
    setSelectedModel(model)
    if (activeConversation) {
      try {
        await api.updateConversation(activeConversation.id, { model })
      } catch {}
    }
  }

  async function onTemperatureChange(temp) {
    setTemperature(temp)
    if (activeConversation) {
      try {
        await api.updateConversation(activeConversation.id, { temperature: temp })
      } catch {}
    }
  }

  // Assistant CRUD handlers
  async function handleCreateAssistant(data) {
    await api.createAssistant(data)
    await loadAssistants()
  }

  async function handleUpdateAssistant(id, data) {
    await api.updateAssistant(id, data)
    await loadAssistants()
  }

  async function handleDeleteAssistant(id) {
    await api.deleteAssistant(id)
    await loadAssistants()
  }

  // Template CRUD handlers
  async function handleCreateTemplate(data) {
    await api.createTemplate(data)
    await loadTemplates()
  }

  async function handleUpdateTemplate(id, data) {
    await api.updateTemplate(id, data)
    await loadTemplates()
  }

  async function handleDeleteTemplate(id) {
    await api.deleteTemplate(id)
    await loadTemplates()
  }

  // Document handlers
  async function handleUploadDocument(file, chatId) {
    setError('')
    try {
      await api.uploadDocument(file, chatId)
      await loadDocuments()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDeleteDocument(docId) {
    setError('')
    try {
      await api.deleteDocument(docId)
      await loadDocuments()
    } catch (e) {
      setError(e.message)
    }
  }

  if (!authChecked) {
    return (
      <div className="app-loading">
        <div className="loading-spinner" />
      </div>
    )
  }

  if (!user) {
    return <LoginScreen onLogin={handleAuth} />
  }

  return (
    <div className="app">
      <Sidebar
        user={user}
        usage={usage}
        conversations={conversations}
        activeId={activeConversation?.id}
        loading={loading}
        assistants={assistants}
        showAdmin={showAdmin}
        onCreateConversation={() => onCreateConversation()}
        onOpenConversation={onOpenConversation}
        onDeleteConversation={onDeleteConversation}
        onSelectAssistant={onSelectAssistant}
        onManageAssistants={() => setShowAssistantManager(true)}
        onManageTemplates={() => setShowTemplateManager(true)}
        onAdmin={() => setShowAdmin(true)}
        onLogout={handleLogout}
      />
      {showAdmin ? (
        <AdminDashboard onClose={() => setShowAdmin(false)} currentUser={user} />
      ) : (
        <ChatArea
          conversation={activeConversation}
          models={models}
          selectedModel={selectedModel}
          temperature={temperature}
          loading={loading}
          streamingContent={streamingContent}
          error={error}
          templates={templates}
          documents={chatDocuments}
          onSend={onSendMessage}
          onModelChange={onModelChange}
          onTemperatureChange={onTemperatureChange}
          onUpload={handleUploadDocument}
          onDeleteDocument={handleDeleteDocument}
        />
      )}

      {showAssistantManager && (
        <AssistantManager
          assistants={assistants}
          isAdmin={user?.is_admin}
          onClose={() => setShowAssistantManager(false)}
          onCreate={handleCreateAssistant}
          onUpdate={handleUpdateAssistant}
          onDelete={handleDeleteAssistant}
        />
      )}

      {showTemplateManager && (
        <TemplateManager
          templates={templates}
          isAdmin={user?.is_admin}
          onClose={() => setShowTemplateManager(false)}
          onCreate={handleCreateTemplate}
          onUpdate={handleUpdateTemplate}
          onDelete={handleDeleteTemplate}
        />
      )}
    </div>
  )
}
