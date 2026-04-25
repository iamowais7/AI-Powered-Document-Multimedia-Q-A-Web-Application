import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Loader2 } from 'lucide-react'
import { documentsApi, mediaApi } from '../services/api'
import { useAppStore } from '../store'
import type { Document, MediaFile } from '../types'

interface Props {
  onUploaded: () => void
}

export default function FileUpload({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const { addDocument, addMediaFile } = useAppStore()

  const onDrop = useCallback(
    async (files: File[]) => {
      if (!files.length) return
      const file = files[0]
      setError('')
      setUploading(true)
      try {
        if (file.type === 'application/pdf') {
          const { data } = await documentsApi.upload(file)
          addDocument(data as Document)
        } else {
          const { data } = await mediaApi.upload(file)
          addMediaFile(data as MediaFile)
        }
        onUploaded()
      } catch (err: unknown) {
        const e = err as { response?: { data?: { detail?: string } } }
        setError(e.response?.data?.detail || 'Upload failed')
      } finally {
        setUploading(false)
      }
    },
    [addDocument, addMediaFile, onUploaded]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'audio/*': ['.mp3', '.wav', '.ogg', '.m4a'],
      'video/*': ['.mp4', '.mov', '.webm', '.mpeg'],
    },
    maxFiles: 1,
    disabled: uploading,
  })

  return (
    <div>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-3 text-center cursor-pointer transition-colors text-xs ${
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
        } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="flex items-center justify-center gap-2 text-blue-600">
            <Loader2 size={14} className="animate-spin" />
            <span>Processing…</span>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 text-gray-500">
            <Upload size={14} />
            <span>{isDragActive ? 'Drop here' : 'Upload PDF / Audio / Video'}</span>
          </div>
        )}
      </div>
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  )
}
