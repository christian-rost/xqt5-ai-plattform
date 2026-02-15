import { useEffect, useState, useCallback } from 'react'
import { api } from './api'
import LoginScreen from './components/LoginScreen'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'

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

  // Sync model/temperature when conversation changes
  useEffect(() => {
    if (activeConversation) {
      if (activeConversation.model) setSelectedModel(activeConversation.model)
      if (activeConversation.temperature != null) setTemperature(activeConversation.temperature)
    }
  }, [activeConversation?.id])

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
  }

  async function onCreateConversation() {
    setLoading(true)
    setError('')
    try {
      const created = await api.createConversation('New Conversation')
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
        async (fullContent) => {
          // Stream complete — finalize
          setStreamingContent(null)
          setLoading(false)

          // Refresh conversation to get stored messages
          const updated = await api.getConversation(activeConversation.id)
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
        onCreateConversation={onCreateConversation}
        onOpenConversation={onOpenConversation}
        onLogout={handleLogout}
      />
      <ChatArea
        conversation={activeConversation}
        models={models}
        selectedModel={selectedModel}
        temperature={temperature}
        loading={loading}
        streamingContent={streamingContent}
        error={error}
        onSend={onSendMessage}
        onModelChange={onModelChange}
        onTemperatureChange={onTemperatureChange}
      />
    </div>
  )
}
