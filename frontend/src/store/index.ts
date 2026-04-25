import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Document, MediaFile, ChatSession, ChatMessage } from '../types'

interface AuthState {
  user: User | null
  token: string | null
  setAuth: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => {
        localStorage.setItem('access_token', token)
        set({ user, token })
      },
      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        set({ user: null, token: null })
      },
    }),
    { name: 'auth-store' }
  )
)

interface AppState {
  documents: Document[]
  mediaFiles: MediaFile[]
  sessions: ChatSession[]
  activeSession: ChatSession | null
  streamingMessage: string
  isStreaming: boolean

  setDocuments: (docs: Document[]) => void
  addDocument: (doc: Document) => void
  removeDocument: (id: number) => void

  setMediaFiles: (files: MediaFile[]) => void
  addMediaFile: (file: MediaFile) => void
  removeMediaFile: (id: number) => void

  setSessions: (sessions: ChatSession[]) => void
  setActiveSession: (session: ChatSession | null) => void
  addMessage: (sessionId: number, message: ChatMessage) => void
  appendStreamChunk: (chunk: string) => void
  setStreaming: (v: boolean) => void
  clearStream: () => void
}

export const useAppStore = create<AppState>((set) => ({
  documents: [],
  mediaFiles: [],
  sessions: [],
  activeSession: null,
  streamingMessage: '',
  isStreaming: false,

  setDocuments: (docs) => set({ documents: docs }),
  addDocument: (doc) => set((s) => ({ documents: [doc, ...s.documents] })),
  removeDocument: (id) => set((s) => ({ documents: s.documents.filter((d) => d.id !== id) })),

  setMediaFiles: (files) => set({ mediaFiles: files }),
  addMediaFile: (file) => set((s) => ({ mediaFiles: [file, ...s.mediaFiles] })),
  removeMediaFile: (id) => set((s) => ({ mediaFiles: s.mediaFiles.filter((f) => f.id !== id) })),

  setSessions: (sessions) => set({ sessions }),
  setActiveSession: (session) => set({ activeSession: session }),
  addMessage: (sessionId, message) =>
    set((s) => ({
      activeSession:
        s.activeSession?.id === sessionId
          ? { ...s.activeSession, messages: [...s.activeSession.messages, message] }
          : s.activeSession,
    })),
  appendStreamChunk: (chunk) => set((s) => ({ streamingMessage: s.streamingMessage + chunk })),
  setStreaming: (v) => set({ isStreaming: v }),
  clearStream: () => set({ streamingMessage: '', isStreaming: false }),
}))
