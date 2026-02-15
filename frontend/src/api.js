const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001'

export const api = {
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`)
    if (!response.ok) throw new Error('Konnte Konversationen nicht laden')
    return response.json()
  },

  async createConversation(title = 'New Conversation') {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    })
    if (!response.ok) throw new Error('Konnte Konversation nicht erstellen')
    return response.json()
  },

  async getConversation(id) {
    const response = await fetch(`${API_BASE}/api/conversations/${id}`)
    if (!response.ok) throw new Error('Konnte Konversation nicht laden')
    return response.json()
  },

  async updateConversation(id, updates) {
    const response = await fetch(`${API_BASE}/api/conversations/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
    if (!response.ok) throw new Error('Konnte Konversation nicht aktualisieren')
    return response.json()
  },

  async listModels() {
    const response = await fetch(`${API_BASE}/api/models`)
    if (!response.ok) throw new Error('Konnte Modelle nicht laden')
    return response.json()
  },

  async sendMessage(id, content, model, temperature) {
    const response = await fetch(`${API_BASE}/api/conversations/${id}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, model, temperature, stream: false }),
    })
    if (!response.ok) throw new Error('Konnte Nachricht nicht senden')
    return response.json()
  },

  async sendMessageStream(id, content, model, temperature, onDelta, onDone, onError) {
    const response = await fetch(`${API_BASE}/api/conversations/${id}/message`, {
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
