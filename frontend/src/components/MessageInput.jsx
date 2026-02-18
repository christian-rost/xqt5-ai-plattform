import { useState } from 'react'
import ModelSelector from './ModelSelector'
import TemperatureSlider from './TemperatureSlider'
import TemplatePicker from './TemplatePicker'
import FileUpload from './FileUpload'
import DocumentList from './DocumentList'

export default function MessageInput({
  models,
  selectedModel,
  temperature,
  imageMode,
  loading,
  templates,
  chatId,
  documents,
  onSend,
  onModelChange,
  onTemperatureChange,
  onImageModeChange,
  onUpload,
  onDeleteDocument,
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
        <div className="model-selector">
          <label className="model-label">Bildquellen</label>
          <select
            className="model-select"
            value={imageMode || 'auto'}
            onChange={(e) => onImageModeChange?.(e.target.value)}
          >
            <option value="auto">Auto</option>
            <option value="on">Ein</option>
            <option value="off">Aus</option>
          </select>
        </div>
        <TemplatePicker
          templates={templates}
          onSelect={handleInsertTemplate}
        />
      </div>
      <div className="input-row">
        {chatId && onUpload && (
          <FileUpload chatId={chatId} onUploadComplete={onUpload} disabled={loading} />
        )}
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
      <DocumentList documents={documents} onDelete={onDeleteDocument} />
    </form>
  )
}
