import { useState } from 'react'
import ModelSelector from './ModelSelector'
import TemperatureSlider from './TemperatureSlider'
import TemplatePicker from './TemplatePicker'

export default function MessageInput({
  models,
  selectedModel,
  temperature,
  loading,
  templates,
  onSend,
  onModelChange,
  onTemperatureChange,
}) {
  const [message, setMessage] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (!message.trim() || loading) return
    onSend(message.trim())
    setMessage('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  function handleInsertTemplate(content) {
    setMessage((prev) => prev ? prev + '\n' + content : content)
  }

  return (
    <form className="input-form" onSubmit={handleSubmit}>
      <div className="input-controls">
        <ModelSelector
          models={models}
          selectedModel={selectedModel}
          onChange={onModelChange}
        />
        <TemperatureSlider
          temperature={temperature}
          onChange={onTemperatureChange}
        />
        <TemplatePicker
          templates={templates}
          onSelect={handleInsertTemplate}
        />
      </div>
      <div className="input-row">
        <textarea
          className="message-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={loading}
        />
        <button
          className="send-button"
          type="submit"
          disabled={loading || !message.trim()}
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </form>
  )
}
