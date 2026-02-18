import { useRef, useState } from 'react'

export default function FileUpload({ chatId, onUploadComplete, disabled }) {
  const fileInputRef = useRef(null)
  const [uploading, setUploading] = useState(false)

  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await onUploadComplete(file, chatId)
    } catch {
      // Error handled by parent
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="file-upload">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.png,.jpg,.jpeg,.webp"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
      <button
        className="upload-btn"
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled || uploading}
        title="Upload PDF, TXT or image"
      >
        {uploading ? '...' : '\u{1F4CE}'}
      </button>
    </div>
  )
}
