import { useEffect, useState } from 'react'
import { api } from '../api'

const TABS = [
  { id: 'users', label: 'Benutzer' },
  { id: 'costs', label: 'Kosten' },
  { id: 'stats', label: 'Statistiken' },
  { id: 'models', label: 'Modelle' },
  { id: 'providers', label: 'Provider' },
  { id: 'audit', label: 'Audit-Logs' },
]

export default function AdminDashboard({ onClose, currentUser }) {
  const [activeTab, setActiveTab] = useState('users')

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <h2>Admin-Dashboard</h2>
        <button className="btn btn-secondary" onClick={onClose}>
          Zurück zum Chat
        </button>
      </div>

      <div className="admin-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`admin-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="admin-content">
        {activeTab === 'users' && <UsersTab currentUser={currentUser} />}
        {activeTab === 'costs' && <CostsTab />}
        {activeTab === 'stats' && <StatsTab />}
        {activeTab === 'models' && <ModelsTab />}
        {activeTab === 'providers' && <ProvidersTab />}
        {activeTab === 'audit' && <AuditTab />}
      </div>
    </div>
  )
}

function UsersTab({ currentUser }) {
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [showInactive, setShowInactive] = useState(false)

  useEffect(() => {
    loadUsers()
  }, [])

  async function loadUsers() {
    try {
      const data = await api.adminListUsers()
      setUsers(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function toggleUser(userId, field, value) {
    setError('')
    try {
      await api.adminUpdateUser(userId, { [field]: value })
      await loadUsers()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDelete(userId, username) {
    if (!confirm(`Benutzer "${username}" wirklich löschen (deaktivieren)?`)) return
    setError('')
    try {
      await api.adminDeleteUser(userId)
      await loadUsers()
    } catch (e) {
      setError(e.message)
    }
  }

  if (loading) return <div className="admin-loading">Laden...</div>

  const filteredUsers = showInactive ? users : users.filter((u) => u.is_active)

  return (
    <div>
      {error && <div className="admin-error">{error}</div>}
      <label className="form-checkbox" style={{ marginBottom: 16 }}>
        <input
          type="checkbox"
          checked={showInactive}
          onChange={() => setShowInactive(!showInactive)}
        />
        Deaktivierte anzeigen
      </label>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Email</th>
            <th>Registriert</th>
            <th>Aktiv</th>
            <th>Admin</th>
            <th>Aktionen</th>
          </tr>
        </thead>
        <tbody>
          {filteredUsers.map((u) => (
            <tr key={u.id} className={!u.is_active ? 'user-inactive' : ''}>
              <td>{u.username}</td>
              <td>{u.email}</td>
              <td>{new Date(u.created_at).toLocaleDateString('de-DE')}</td>
              <td>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={u.is_active}
                    onChange={() => toggleUser(u.id, 'is_active', !u.is_active)}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </td>
              <td>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={u.is_admin}
                    onChange={() => toggleUser(u.id, 'is_admin', !u.is_admin)}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </td>
              <td>
                <button
                  className="btn btn-danger btn-small"
                  disabled={currentUser && u.id === currentUser.id}
                  onClick={() => handleDelete(u.id, u.username)}
                >
                  Löschen
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CostsTab() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  useEffect(() => {
    loadUsage()
  }, [])

  async function loadUsage(start, end) {
    setLoading(true)
    setError('')
    try {
      const result = await api.adminGetUsage(start, end)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleApply() {
    loadUsage(startDate || undefined, endDate || undefined)
  }

  function handleReset() {
    setStartDate('')
    setEndDate('')
    loadUsage()
  }

  if (loading && !data) return <div className="admin-loading">Laden...</div>
  if (error && !data) return <div className="admin-error">{error}</div>
  if (!data) return null

  const s = data.summary

  return (
    <div>
      {/* Date Filters */}
      <div className="token-filters">
        <div className="token-filter-row">
          <div className="token-filter-group">
            <label>Startdatum</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div className="token-filter-group">
            <label>Enddatum</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <button className="btn btn-primary btn-small" onClick={handleApply} disabled={loading}
            style={{ alignSelf: 'flex-end' }}>
            {loading ? 'Laden...' : 'Anwenden'}
          </button>
          {(startDate || endDate) && (
            <button className="btn btn-secondary btn-small" onClick={handleReset}
              style={{ alignSelf: 'flex-end' }}>
              Zurücksetzen
            </button>
          )}
        </div>
      </div>

      {error && <div className="admin-error">{error}</div>}

      {/* 4 Summary Cards */}
      <div className="admin-cards">
        <div className="admin-card">
          <div className="admin-card-label">Anfragen</div>
          <div className="admin-card-value">{s.total_requests.toLocaleString()}</div>
        </div>
        <div className="admin-card">
          <div className="admin-card-label">Gesamt-Tokens</div>
          <div className="admin-card-value">{s.total_tokens.toLocaleString()}</div>
        </div>
        <div className="admin-card">
          <div className="admin-card-label">Geschätzte Kosten</div>
          <div className="admin-card-value">${s.estimated_cost.toFixed(4)}</div>
        </div>
        <div className="admin-card">
          <div className="admin-card-label">Prompt / Completion</div>
          <div className="admin-card-value">{s.total_prompt_tokens.toLocaleString()}</div>
          <div className="admin-card-sub">{s.total_completion_tokens.toLocaleString()} Completion</div>
        </div>
      </div>

      {/* By Provider */}
      <h3 className="admin-section-title">Nach Provider</h3>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Provider</th>
            <th>Anfragen</th>
            <th>Tokens</th>
            <th>Kosten</th>
          </tr>
        </thead>
        <tbody>
          {data.by_provider.map((p) => (
            <tr key={p.provider}>
              <td><span className="provider-badge">{p.provider}</span></td>
              <td>{p.requests.toLocaleString()}</td>
              <td>{p.tokens.toLocaleString()}</td>
              <td>${p.estimated_cost.toFixed(4)}</td>
            </tr>
          ))}
          {data.by_provider.length === 0 && (
            <tr><td colSpan="4" className="admin-empty-cell">Keine Daten</td></tr>
          )}
        </tbody>
      </table>

      {/* By Model */}
      <h3 className="admin-section-title">Nach Modell</h3>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Modell</th>
            <th>Provider</th>
            <th>Anfragen</th>
            <th>Avg Tokens</th>
            <th>Kosten</th>
          </tr>
        </thead>
        <tbody>
          {data.by_model.map((m) => (
            <tr key={m.model}>
              <td><code>{m.model}</code></td>
              <td><span className="provider-badge">{m.provider}</span></td>
              <td>{m.requests.toLocaleString()}</td>
              <td>{m.avg_tokens.toLocaleString()}</td>
              <td>${m.estimated_cost.toFixed(4)}</td>
            </tr>
          ))}
          {data.by_model.length === 0 && (
            <tr><td colSpan="5" className="admin-empty-cell">Keine Daten</td></tr>
          )}
        </tbody>
      </table>

      {/* By User */}
      <h3 className="admin-section-title">Nach Benutzer</h3>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Anfragen</th>
            <th>Tokens</th>
            <th>Kosten</th>
          </tr>
        </thead>
        <tbody>
          {data.by_user.map((u) => (
            <tr key={u.user_id}>
              <td>{u.username}</td>
              <td>{u.requests.toLocaleString()}</td>
              <td>{u.tokens.toLocaleString()}</td>
              <td>${u.estimated_cost.toFixed(4)}</td>
            </tr>
          ))}
          {data.by_user.length === 0 && (
            <tr><td colSpan="4" className="admin-empty-cell">Keine Daten</td></tr>
          )}
        </tbody>
      </table>

      {/* Daily Usage */}
      <h3 className="admin-section-title">Tägliche Nutzung</h3>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Datum</th>
            <th>Anfragen</th>
            <th>Tokens</th>
            <th>Kosten</th>
          </tr>
        </thead>
        <tbody>
          {data.daily.map((d) => (
            <tr key={d.date}>
              <td>{new Date(d.date + 'T00:00:00').toLocaleDateString('de-DE')}</td>
              <td>{d.requests.toLocaleString()}</td>
              <td>{d.tokens.toLocaleString()}</td>
              <td>${d.estimated_cost.toFixed(4)}</td>
            </tr>
          ))}
          {data.daily.length === 0 && (
            <tr><td colSpan="4" className="admin-empty-cell">Keine Daten</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function StatsTab() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.adminGetStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="admin-loading">Laden...</div>
  if (error) return <div className="admin-error">{error}</div>
  if (!stats) return null

  const items = [
    { label: 'Benutzer gesamt', value: stats.total_users },
    { label: 'Aktive Benutzer', value: stats.active_users },
    { label: 'Chats', value: stats.total_chats },
    { label: 'Nachrichten', value: stats.total_messages },
    { label: 'Assistenten', value: stats.total_assistants },
    { label: 'Templates', value: stats.total_templates },
  ]

  return (
    <div className="admin-cards">
      {items.map((item) => (
        <div className="admin-card" key={item.label}>
          <div className="admin-card-label">{item.label}</div>
          <div className="admin-card-value">{item.value}</div>
        </div>
      ))}
    </div>
  )
}

function ModelsTab() {
  const [models, setModels] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ model_id: '', provider: '', display_name: '', sort_order: 0, deployment_name: '' })

  useEffect(() => {
    loadModels()
  }, [])

  async function loadModels() {
    try {
      const data = await api.adminListModels()
      setModels(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleToggle(id, field, value) {
    setError('')
    try {
      await api.adminUpdateModel(id, { [field]: value })
      await loadModels()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleSetDefault(id) {
    setError('')
    try {
      await api.adminUpdateModel(id, { is_default: true })
      await loadModels()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDelete(id) {
    if (!confirm('Modell wirklich löschen?')) return
    setError('')
    try {
      await api.adminDeleteModel(id)
      await loadModels()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    try {
      const payload = { ...form }
      if (!payload.deployment_name) delete payload.deployment_name
      await api.adminCreateModel(payload)
      setForm({ model_id: '', provider: '', display_name: '', sort_order: 0, deployment_name: '' })
      setShowForm(false)
      await loadModels()
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) return <div className="admin-loading">Laden...</div>

  return (
    <div>
      {error && <div className="admin-error">{error}</div>}

      <button className="btn btn-primary btn-small" onClick={() => setShowForm(!showForm)} style={{ marginBottom: 16 }}>
        {showForm ? 'Abbrechen' : 'Neues Modell'}
      </button>

      {showForm && (
        <form className="admin-model-form" onSubmit={handleCreate}>
          <div className="form-row">
            <div className="form-group">
              <label>Model ID</label>
              <input className="form-input" placeholder="provider/model-name" value={form.model_id}
                onChange={(e) => setForm({ ...form, model_id: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Provider</label>
              <input className="form-input" placeholder="openai" value={form.provider}
                onChange={(e) => setForm({ ...form, provider: e.target.value })} required />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Display Name</label>
              <input className="form-input" placeholder="GPT-5.1" value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Sort Order</label>
              <input className="form-input" type="number" value={form.sort_order}
                onChange={(e) => setForm({ ...form, sort_order: parseInt(e.target.value) || 0 })} />
            </div>
          </div>
          {form.provider === 'azure' && (
            <div className="form-row">
              <div className="form-group">
                <label>Deployment Name (Azure)</label>
                <input className="form-input" placeholder="z.B. my-gpt5-deployment" value={form.deployment_name}
                  onChange={(e) => setForm({ ...form, deployment_name: e.target.value })} />
              </div>
            </div>
          )}
          <button className="btn btn-primary btn-small" type="submit">Hinzufügen</button>
        </form>
      )}

      <table className="admin-table">
        <thead>
          <tr>
            <th>Model ID</th>
            <th>Provider</th>
            <th>Display Name</th>
            <th>Deployment</th>
            <th>Aktiviert</th>
            <th>Default</th>
            <th>Aktionen</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <tr key={m.id}>
              <td><code>{m.model_id}</code></td>
              <td>{m.provider}</td>
              <td>{m.display_name}</td>
              <td>{m.deployment_name || '-'}</td>
              <td>
                <label className="toggle-switch">
                  <input type="checkbox" checked={m.is_enabled}
                    onChange={() => handleToggle(m.id, 'is_enabled', !m.is_enabled)} />
                  <span className="toggle-slider"></span>
                </label>
              </td>
              <td>
                <input type="radio" name="default_model" checked={m.is_default}
                  onChange={() => handleSetDefault(m.id)} />
              </td>
              <td>
                <button className="btn btn-danger btn-small" onClick={() => handleDelete(m.id)}>
                  Löschen
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ProvidersTab() {
  const [providers, setProviders] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [keyInputs, setKeyInputs] = useState({})
  const [azureInputs, setAzureInputs] = useState({ endpoint_url: '', api_version: '' })
  const [saving, setSaving] = useState({})
  const [testing, setTesting] = useState({})
  const [testResults, setTestResults] = useState({})

  useEffect(() => {
    loadProviders()
  }, [])

  async function loadProviders() {
    try {
      const data = await api.adminListProviders()
      setProviders(data)
      const azure = data.find((p) => p.provider === 'azure')
      if (azure) {
        setAzureInputs((prev) => ({
          endpoint_url: azure.endpoint_url || prev.endpoint_url || '',
          api_version: azure.api_version || prev.api_version || '',
        }))
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(provider) {
    const key = (keyInputs[provider] || '').trim()
    if (!key) return
    setSaving((s) => ({ ...s, [provider]: true }))
    setError('')
    setTestResults((r) => ({ ...r, [provider]: null }))
    try {
      const extra = provider === 'azure' ? {
        endpoint_url: azureInputs.endpoint_url.trim(),
        api_version: azureInputs.api_version.trim(),
      } : {}
      await api.adminSetProviderKey(provider, key, extra)
      setKeyInputs((k) => ({ ...k, [provider]: '' }))
      await loadProviders()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving((s) => ({ ...s, [provider]: false }))
    }
  }

  async function handleDelete(provider) {
    if (!confirm(`API-Key für ${provider} wirklich deaktivieren?`)) return
    setError('')
    setTestResults((r) => ({ ...r, [provider]: null }))
    try {
      await api.adminDeleteProviderKey(provider)
      await loadProviders()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleTest(provider) {
    setTesting((t) => ({ ...t, [provider]: true }))
    setTestResults((r) => ({ ...r, [provider]: null }))
    try {
      const result = await api.adminTestProvider(provider)
      setTestResults((r) => ({ ...r, [provider]: result }))
    } catch (e) {
      setTestResults((r) => ({ ...r, [provider]: { success: false, error: e.message } }))
    } finally {
      setTesting((t) => ({ ...t, [provider]: false }))
    }
  }

  function sourceBadge(source) {
    if (source === 'db') return <span className="badge badge-success">DB Key</span>
    if (source === 'env') return <span className="badge badge-info">Env Var</span>
    return <span className="badge badge-warning">Nicht konfiguriert</span>
  }

  if (loading) return <div className="admin-loading">Laden...</div>

  return (
    <div>
      {error && <div className="admin-error">{error}</div>}

      <div className="provider-grid">
        {providers.map((p) => (
          <div className="provider-card" key={p.provider}>
            <div className="provider-card-header">
              <strong>{p.display_name}</strong>
              {sourceBadge(p.source)}
            </div>

            <div className="provider-card-body">
              <div className="provider-key-row">
                <input
                  className="form-input"
                  type="password"
                  placeholder="API-Key eingeben..."
                  value={keyInputs[p.provider] || ''}
                  onChange={(e) => setKeyInputs((k) => ({ ...k, [p.provider]: e.target.value }))}
                />
              </div>

              {p.provider === 'azure' && (
                <div className="azure-extra-fields">
                  <div className="provider-key-row">
                    <input
                      className="form-input"
                      type="text"
                      placeholder="Endpoint-URL (z.B. https://my-resource.openai.azure.com)"
                      value={azureInputs.endpoint_url}
                      onChange={(e) => setAzureInputs((a) => ({ ...a, endpoint_url: e.target.value }))}
                    />
                  </div>
                  <div className="provider-key-row">
                    <input
                      className="form-input"
                      type="text"
                      placeholder="API-Version (z.B. 2024-12-01-preview)"
                      value={azureInputs.api_version}
                      onChange={(e) => setAzureInputs((a) => ({ ...a, api_version: e.target.value }))}
                    />
                  </div>
                </div>
              )}

              <div className="provider-actions">
                <button
                  className="btn btn-primary btn-small"
                  onClick={() => handleSave(p.provider)}
                  disabled={saving[p.provider] || !keyInputs[p.provider]?.trim()}
                >
                  {saving[p.provider] ? 'Speichern...' : 'Speichern'}
                </button>

                <button
                  className="btn btn-secondary btn-small"
                  onClick={() => handleTest(p.provider)}
                  disabled={testing[p.provider] || p.source === 'none'}
                >
                  {testing[p.provider] ? 'Teste...' : 'Testen'}
                </button>

                {p.has_db && (
                  <button
                    className="btn btn-danger btn-small"
                    onClick={() => handleDelete(p.provider)}
                  >
                    DB-Key löschen
                  </button>
                )}
              </div>

              {testResults[p.provider] && (
                <div className={`provider-test-result ${testResults[p.provider].success ? 'success' : 'error'}`}>
                  {testResults[p.provider].success
                    ? testResults[p.provider].message
                    : testResults[p.provider].error}
                </div>
              )}

              {p.has_env && p.source === 'db' && (
                <div className="provider-hint">Env-Var als Fallback vorhanden</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function AuditTab() {
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [actionFilter, setActionFilter] = useState('')
  const LIMIT = 50

  useEffect(() => {
    loadLogs(true)
  }, [actionFilter])

  async function loadLogs(reset = false) {
    const newOffset = reset ? 0 : offset
    setLoading(true)
    setError('')
    try {
      const data = await api.adminGetAuditLogs(LIMIT, newOffset, actionFilter || null, null)
      if (reset) {
        setLogs(data)
        setOffset(LIMIT)
      } else {
        setLogs((prev) => [...prev, ...data])
        setOffset(newOffset + LIMIT)
      }
      setHasMore(data.length === LIMIT)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {error && <div className="admin-error">{error}</div>}

      <div className="admin-filters">
        <input
          className="form-input"
          placeholder="Filter nach Aktion (z.B. auth.login)"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          style={{ maxWidth: 300 }}
        />
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>Zeitstempel</th>
            <th>Benutzer</th>
            <th>Aktion</th>
            <th>Ziel</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>{new Date(log.created_at).toLocaleString('de-DE')}</td>
              <td>{log.username || log.user_id || '-'}</td>
              <td><code>{log.action}</code></td>
              <td>{log.target_type ? `${log.target_type}` : '-'}</td>
              <td className="admin-metadata-cell">
                {log.metadata && Object.keys(log.metadata).length > 0
                  ? JSON.stringify(log.metadata)
                  : '-'}
              </td>
            </tr>
          ))}
          {logs.length === 0 && !loading && (
            <tr><td colSpan="5" className="admin-empty-cell">Keine Audit-Logs vorhanden</td></tr>
          )}
        </tbody>
      </table>

      {hasMore && (
        <button className="btn btn-secondary" onClick={() => loadLogs(false)} disabled={loading}
          style={{ marginTop: 16 }}>
          {loading ? 'Laden...' : 'Mehr laden'}
        </button>
      )}
    </div>
  )
}
