const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001'

function getAccessToken() {
  return localStorage.getItem('access_token')
}

function getRefreshToken() {
  return localStorage.getItem('refresh_token')
}

function setTokens(accessToken, refreshToken) {
  localStorage.setItem('access_token', accessToken)
  if (refreshToken) localStorage.setItem('refresh_token', refreshToken)
}

function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

function authHeaders() {
  const token = getAccessToken()
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

async function authFetch(url, options = {}) {
  const headers = { ...authHeaders(), ...(options.headers || {}) }
  let response = await fetch(url, { ...options, headers })

  // Try refresh on 401
  if (response.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      const retryHeaders = { ...authHeaders(), ...(options.headers || {}) }
      response = await fetch(url, { ...options, headers: retryHeaders })
    }
  }

  return response
}

async function tryRefresh() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) {
      clearTokens()
      return false
    }
    const data = await response.json()
    setTokens(data.access_token, null)
    return true
  } catch {
    clearTokens()
    return false
  }
}

export const api = {
  // Auth
  async register(username, email, password) {
    const response = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || 'Registrierung fehlgeschlagen')
    }
    const data = await response.json()
    setTokens(data.access_token, data.refresh_token)
    return data.user
  },

  async login(username, password) {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || 'Login fehlgeschlagen')
    }
    const data = await response.json()
    setTokens(data.access_token, data.refresh_token)
    return data.user
  },

  async getMe() {
    const token = getAccessToken()
    if (!token) return null
    const response = await authFetch(`${API_BASE}/api/auth/me`)
    if (!response.ok) {
      clearTokens()
      return null
    }
    return response.json()
  },

  logout() {
    clearTokens()
  },

  // Usage
  async getUsage() {
    const response = await authFetch(`${API_BASE}/api/usage`)
    if (!response.ok) throw new Error('Konnte Nutzung nicht laden')
    return response.json()
  },

  // Conversations
  async listConversations() {
    const response = await authFetch(`${API_BASE}/api/conversations`)
    if (!response.ok) throw new Error('Konnte Konversationen nicht laden')
    return response.json()
  },

  async createConversation(title = 'New Conversation', assistantId = null) {
    const payload = { title }
    if (assistantId) payload.assistant_id = assistantId
    const response = await authFetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) throw new Error('Konnte Konversation nicht erstellen')
    return response.json()
  },

  async getConversation(id) {
    const response = await authFetch(`${API_BASE}/api/conversations/${id}`)
    if (!response.ok) throw new Error('Konnte Konversation nicht laden')
    return response.json()
  },

  async updateConversation(id, updates) {
    const response = await authFetch(`${API_BASE}/api/conversations/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
    if (!response.ok) throw new Error('Konnte Konversation nicht aktualisieren')
    return response.json()
  },

  async deleteConversation(id) {
    const response = await authFetch(`${API_BASE}/api/conversations/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error('Konnte Konversation nicht löschen')
    return response.json()
  },

  async listModels() {
    const response = await fetch(`${API_BASE}/api/models`)
    if (!response.ok) throw new Error('Konnte Modelle nicht laden')
    return response.json()
  },

  async sendMessage(id, content, model, temperature) {
    const response = await authFetch(`${API_BASE}/api/conversations/${id}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, model, temperature, stream: false }),
    })
    if (!response.ok) throw new Error('Konnte Nachricht nicht senden')
    return response.json()
  },

  // Assistants
  async listAssistants() {
    const response = await authFetch(`${API_BASE}/api/assistants`)
    if (!response.ok) throw new Error('Konnte Assistenten nicht laden')
    return response.json()
  },

  async createAssistant(data) {
    const response = await authFetch(`${API_BASE}/api/assistants`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Konnte Assistenten nicht erstellen')
    }
    return response.json()
  },

  async updateAssistant(id, data) {
    const response = await authFetch(`${API_BASE}/api/assistants/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) throw new Error('Konnte Assistenten nicht aktualisieren')
    return response.json()
  },

  async deleteAssistant(id) {
    const response = await authFetch(`${API_BASE}/api/assistants/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error('Konnte Assistenten nicht löschen')
    return response.json()
  },

  // Templates
  async listTemplates() {
    const response = await authFetch(`${API_BASE}/api/templates`)
    if (!response.ok) throw new Error('Konnte Templates nicht laden')
    return response.json()
  },

  async createTemplate(data) {
    const response = await authFetch(`${API_BASE}/api/templates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Konnte Template nicht erstellen')
    }
    return response.json()
  },

  async updateTemplate(id, data) {
    const response = await authFetch(`${API_BASE}/api/templates/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) throw new Error('Konnte Template nicht aktualisieren')
    return response.json()
  },

  async deleteTemplate(id) {
    const response = await authFetch(`${API_BASE}/api/templates/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error('Konnte Template nicht löschen')
    return response.json()
  },

  // Admin
  async adminListUsers() {
    const response = await authFetch(`${API_BASE}/api/admin/users`)
    if (!response.ok) throw new Error('Konnte Benutzer nicht laden')
    return response.json()
  },

  async adminUpdateUser(userId, data) {
    const response = await authFetch(`${API_BASE}/api/admin/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Konnte Benutzer nicht aktualisieren')
    }
    return response.json()
  },

  async adminGetUsage() {
    const response = await authFetch(`${API_BASE}/api/admin/usage`)
    if (!response.ok) throw new Error('Konnte Nutzungsdaten nicht laden')
    return response.json()
  },

  async adminGetStats() {
    const response = await authFetch(`${API_BASE}/api/admin/stats`)
    if (!response.ok) throw new Error('Konnte Statistiken nicht laden')
    return response.json()
  },

  async adminListModels() {
    const response = await authFetch(`${API_BASE}/api/admin/models`)
    if (!response.ok) throw new Error('Konnte Modell-Konfigurationen nicht laden')
    return response.json()
  },

  async adminCreateModel(data) {
    const response = await authFetch(`${API_BASE}/api/admin/models`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Konnte Modell nicht erstellen')
    }
    return response.json()
  },

  async adminUpdateModel(id, data) {
    const response = await authFetch(`${API_BASE}/api/admin/models/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!response.ok) throw new Error('Konnte Modell nicht aktualisieren')
    return response.json()
  },

  async adminDeleteModel(id) {
    const response = await authFetch(`${API_BASE}/api/admin/models/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error('Konnte Modell nicht löschen')
    return response.json()
  },

  // Provider Keys
  async adminListProviders() {
    const response = await authFetch(`${API_BASE}/api/admin/providers`)
    if (!response.ok) throw new Error('Konnte Provider nicht laden')
    return response.json()
  },

  async adminSetProviderKey(provider, apiKey) {
    const response = await authFetch(`${API_BASE}/api/admin/providers/${provider}/key`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey }),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Konnte Key nicht speichern')
    }
    return response.json()
  },

  async adminDeleteProviderKey(provider) {
    const response = await authFetch(`${API_BASE}/api/admin/providers/${provider}/key`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error('Konnte Key nicht löschen')
    return response.json()
  },

  async adminTestProvider(provider) {
    const response = await authFetch(`${API_BASE}/api/admin/providers/${provider}/test`, {
      method: 'POST',
    })
    if (!response.ok) throw new Error('Test fehlgeschlagen')
    return response.json()
  },

  async adminGetAuditLogs(limit = 100, offset = 0, action = null, userId = null) {
    let url = `${API_BASE}/api/admin/audit-logs?limit=${limit}&offset=${offset}`
    if (action) url += `&action=${encodeURIComponent(action)}`
    if (userId) url += `&user_id=${encodeURIComponent(userId)}`
    const response = await authFetch(url)
    if (!response.ok) throw new Error('Konnte Audit-Logs nicht laden')
    return response.json()
  },

  async sendMessageStream(id, content, model, temperature, onDelta, onDone, onError) {
    const response = await authFetch(`${API_BASE}/api/conversations/${id}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, model, temperature, stream: true }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(text || 'Konnte Nachricht nicht senden')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.error) {
            onError(data.error)
            return
          }
          if (data.delta) {
            onDelta(data.delta)
          }
          if (data.done) {
            await onDone(data.content)
            return
          }
        } catch {
          // Skip malformed JSON lines
        }
      }
    }
  },
}
