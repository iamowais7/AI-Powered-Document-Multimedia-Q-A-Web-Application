import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore, useAppStore } from '../store'
import { documentsApi, mediaApi, chatApi } from '../services/api'
import FileUpload from '../components/FileUpload'
import ChatInterface from '../components/ChatInterface'
import SummaryPanel from '../components/SummaryPanel'
import { LogOut, FileText, Music, Video, MessageSquare, ChevronRight } from 'lucide-react'
import type { Document, MediaFile, ChatSession } from '../types'

export default function Dashboard() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { documents, mediaFiles, sessions, setDocuments, setMediaFiles, setSessions, setActiveSession, activeSession } = useAppStore()
  const [activeTab, setActiveTab] = useState<'docs' | 'media' | 'sessions'>('docs')
  const [loading, setLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState<{ type: 'doc'; item: Document } | { type: 'media'; item: MediaFile } | null>(null)

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    setLoading(true)
    try {
      const [docsRes, mediaRes, sessionsRes] = await Promise.all([
        documentsApi.list(),
        mediaApi.list(),
        chatApi.listSessions(),
      ])
      setDocuments(docsRes.data.documents)
      setMediaFiles(mediaRes.data.media_files)
      setSessions(sessionsRes.data)
    } finally {
      setLoading(false)
    }
  }

  const handleStartChat = async (type: 'doc' | 'media', id: number, name: string) => {
    const payload = type === 'doc' ? { document_id: id, title: `Chat: ${name}` } : { media_file_id: id, title: `Chat: ${name}` }
    const { data } = await chatApi.createSession(payload)
    setSessions([data, ...sessions])
    setActiveSession({ ...data, messages: [] })
    setSelectedItem(null)
  }

  const handleOpenSession = async (session: ChatSession) => {
    const { data } = await chatApi.getSession(session.id)
    setActiveSession(data)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDuration = (secs: number | null) => {
    if (!secs) return ''
    const m = Math.floor(secs / 60)
    const s = Math.floor(secs % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <div className="w-72 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">DocQA</h1>
          <p className="text-sm text-gray-500 mt-0.5">Hi, {user?.username}</p>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          {[
            { key: 'docs', label: 'Docs', icon: FileText },
            { key: 'media', label: 'Media', icon: Music },
            { key: 'sessions', label: 'Chats', icon: MessageSquare },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key as typeof activeTab)}
              className={`flex-1 flex flex-col items-center py-2 text-xs font-medium transition-colors ${
                activeTab === key ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon size={16} className="mb-0.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Upload Button */}
        <div className="p-3">
          <FileUpload onUploaded={loadAll} />
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-400 text-sm">Loading…</div>
          ) : activeTab === 'docs' ? (
            documents.length === 0 ? (
              <p className="p-4 text-center text-gray-400 text-sm">No documents yet</p>
            ) : (
              documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => setSelectedItem({ type: 'doc', item: doc })}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center gap-3 border-b border-gray-100 ${
                    selectedItem?.type === 'doc' && selectedItem.item.id === doc.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <FileText size={16} className="text-blue-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{doc.original_filename}</p>
                    <p className="text-xs text-gray-400">{formatSize(doc.file_size)} · {doc.page_count} pages</p>
                  </div>
                  <ChevronRight size={14} className="text-gray-300 ml-auto flex-shrink-0" />
                </button>
              ))
            )
          ) : activeTab === 'media' ? (
            mediaFiles.length === 0 ? (
              <p className="p-4 text-center text-gray-400 text-sm">No media files yet</p>
            ) : (
              mediaFiles.map((mf) => (
                <button
                  key={mf.id}
                  onClick={() => setSelectedItem({ type: 'media', item: mf })}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center gap-3 border-b border-gray-100 ${
                    selectedItem?.type === 'media' && selectedItem.item.id === mf.id ? 'bg-blue-50' : ''
                  }`}
                >
                  {mf.media_type === 'video' ? (
                    <Video size={16} className="text-purple-500 flex-shrink-0" />
                  ) : (
                    <Music size={16} className="text-green-500 flex-shrink-0" />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{mf.original_filename}</p>
                    <p className="text-xs text-gray-400">{formatSize(mf.file_size)} · {formatDuration(mf.duration)}</p>
                  </div>
                  <ChevronRight size={14} className="text-gray-300 ml-auto flex-shrink-0" />
                </button>
              ))
            )
          ) : (
            sessions.length === 0 ? (
              <p className="p-4 text-center text-gray-400 text-sm">No chats yet</p>
            ) : (
              sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => handleOpenSession(s)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center gap-3 border-b border-gray-100 ${
                    activeSession?.id === s.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <MessageSquare size={16} className="text-gray-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{s.title}</p>
                    <p className="text-xs text-gray-400">{new Date(s.created_at).toLocaleDateString()}</p>
                  </div>
                </button>
              ))
            )
          )}
        </div>

        <button onClick={handleLogout} className="p-4 flex items-center gap-2 text-gray-500 hover:text-red-500 text-sm border-t border-gray-200">
          <LogOut size={16} />
          Sign Out
        </button>
      </div>

      {/* Main area */}
      <div className="flex-1 flex overflow-hidden">
        {activeSession ? (
          <ChatInterface onBack={() => setActiveSession(null)} />
        ) : selectedItem ? (
          <SummaryPanel
            item={selectedItem}
            onStartChat={handleStartChat}
            onClose={() => setSelectedItem(null)}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-center">
            <div>
              <div className="text-6xl mb-4">🤖</div>
              <h2 className="text-2xl font-semibold text-gray-700">Welcome to DocQA</h2>
              <p className="text-gray-500 mt-2 max-w-sm">
                Upload a PDF, audio, or video file from the sidebar, then start a chat to ask questions.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
