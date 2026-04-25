import { useState } from 'react'
import { X, MessageSquare, FileText, Music, Video, Clock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import type { Document, MediaFile } from '../types'

interface Props {
  item: { type: 'doc'; item: Document } | { type: 'media'; item: MediaFile }
  onStartChat: (type: 'doc' | 'media', id: number, name: string) => void
  onClose: () => void
}

export default function SummaryPanel({ item, onStartChat, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<'summary' | 'transcript'>('summary')
  const isDoc = item.type === 'doc'
  const doc = isDoc ? item.item : null
  const media = !isDoc ? item.item : null

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = Math.floor(secs % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const summary = isDoc ? doc!.summary : media!.summary
  const name = isDoc ? doc!.original_filename : media!.original_filename

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3">
        {isDoc ? (
          <FileText size={20} className="text-blue-500" />
        ) : media!.media_type === 'video' ? (
          <Video size={20} className="text-purple-500" />
        ) : (
          <Music size={20} className="text-green-500" />
        )}
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold text-gray-900 truncate">{name}</h2>
          <p className="text-xs text-gray-400">
            {isDoc ? `${doc!.page_count} pages` : `Duration: ${formatTime(media!.duration || 0)}`}
          </p>
        </div>
        <button
          onClick={() => onStartChat(item.type, item.item.id, name)}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <MessageSquare size={14} />
          Start Chat
        </button>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 ml-2">
          <X size={18} />
        </button>
      </div>

      {/* Tabs */}
      {!isDoc && (
        <div className="bg-white border-b border-gray-200 px-6 flex gap-4">
          {(['summary', 'transcript'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-3 text-sm font-medium border-b-2 transition-colors capitalize ${
                activeTab === tab ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {(isDoc || activeTab === 'summary') && (
          <div className="max-w-3xl">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Summary</h3>
            {summary ? (
              <div className="prose prose-sm max-w-none text-gray-700">
                <ReactMarkdown>{summary}</ReactMarkdown>
              </div>
            ) : (
              <p className="text-gray-400 italic">No summary available.</p>
            )}
          </div>
        )}

        {!isDoc && activeTab === 'transcript' && (
          <div className="max-w-3xl">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Transcript</h3>
            {media!.segments && media!.segments.length > 0 ? (
              <div className="space-y-3">
                {media!.segments.map((seg, i) => (
                  <div key={i} className="flex gap-3 group">
                    <span className="flex items-start gap-1 text-xs text-blue-500 font-mono whitespace-nowrap mt-0.5">
                      <Clock size={11} className="mt-0.5" />
                      {formatTime(seg.start)}
                    </span>
                    <p className="text-sm text-gray-700">{seg.text}</p>
                  </div>
                ))}
              </div>
            ) : media!.transcription ? (
              <p className="text-sm text-gray-700 leading-relaxed">{media!.transcription}</p>
            ) : (
              <p className="text-gray-400 italic">No transcript available.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
