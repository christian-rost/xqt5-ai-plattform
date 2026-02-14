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

  async sendMessage(id, content) {
    const response = await fetch(`${API_BASE}/api/conversations/${id}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!response.ok) throw new Error('Konnte Nachricht nicht senden')
    return response.json()
  },
}
