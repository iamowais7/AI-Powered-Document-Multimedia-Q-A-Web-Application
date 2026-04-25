import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore, useAppStore } from '../store'
import type { User, Document, MediaFile, ChatMessage } from '../types'

const mockUser: User = { id: 1, email: 'a@a.com', username: 'alice', is_active: true, created_at: '2024-01-01' }
const mockDoc: Document = {
  id: 1, filename: 'f.pdf', original_filename: 'f.pdf', file_size: 100,
  content_type: 'application/pdf', extracted_text: 'text', summary: 'sum', page_count: 1, created_at: '2024-01-01',
}
const mockMedia: MediaFile = {
  id: 1, filename: 'v.mp4', original_filename: 'v.mp4', file_size: 200,
  content_type: 'video/mp4', media_type: 'video', duration: 60, transcription: 't', summary: 's',
  segments: [], created_at: '2024-01-01',
}

describe('useAuthStore', () => {
  it('setAuth stores user and token', () => {
    useAuthStore.getState().setAuth(mockUser, 'token123')
    expect(useAuthStore.getState().user).toEqual(mockUser)
    expect(useAuthStore.getState().token).toBe('token123')
  })

  it('logout clears user and token', () => {
    useAuthStore.getState().setAuth(mockUser, 'token123')
    useAuthStore.getState().logout()
    expect(useAuthStore.getState().user).toBeNull()
    expect(useAuthStore.getState().token).toBeNull()
  })
})

describe('useAppStore — documents', () => {
  beforeEach(() => useAppStore.setState({ documents: [] }))

  it('setDocuments replaces list', () => {
    useAppStore.getState().setDocuments([mockDoc])
    expect(useAppStore.getState().documents).toHaveLength(1)
  })

  it('addDocument prepends', () => {
    useAppStore.getState().setDocuments([{ ...mockDoc, id: 2 }])
    useAppStore.getState().addDocument(mockDoc)
    expect(useAppStore.getState().documents[0].id).toBe(1)
  })

  it('removeDocument removes by id', () => {
    useAppStore.getState().setDocuments([mockDoc])
    useAppStore.getState().removeDocument(1)
    expect(useAppStore.getState().documents).toHaveLength(0)
  })
})

describe('useAppStore — media', () => {
  beforeEach(() => useAppStore.setState({ mediaFiles: [] }))

  it('setMediaFiles replaces list', () => {
    useAppStore.getState().setMediaFiles([mockMedia])
    expect(useAppStore.getState().mediaFiles).toHaveLength(1)
  })

  it('addMediaFile prepends', () => {
    useAppStore.getState().setMediaFiles([{ ...mockMedia, id: 2 }])
    useAppStore.getState().addMediaFile(mockMedia)
    expect(useAppStore.getState().mediaFiles[0].id).toBe(1)
  })

  it('removeMediaFile removes by id', () => {
    useAppStore.getState().setMediaFiles([mockMedia])
    useAppStore.getState().removeMediaFile(1)
    expect(useAppStore.getState().mediaFiles).toHaveLength(0)
  })
})

describe('useAppStore — streaming', () => {
  it('appendStreamChunk concatenates', () => {
    useAppStore.setState({ streamingMessage: '' })
    useAppStore.getState().appendStreamChunk('Hello')
    useAppStore.getState().appendStreamChunk(' world')
    expect(useAppStore.getState().streamingMessage).toBe('Hello world')
  })

  it('clearStream resets', () => {
    useAppStore.setState({ streamingMessage: 'text', isStreaming: true })
    useAppStore.getState().clearStream()
    expect(useAppStore.getState().streamingMessage).toBe('')
    expect(useAppStore.getState().isStreaming).toBe(false)
  })

  it('setStreaming toggles', () => {
    useAppStore.getState().setStreaming(true)
    expect(useAppStore.getState().isStreaming).toBe(true)
    useAppStore.getState().setStreaming(false)
    expect(useAppStore.getState().isStreaming).toBe(false)
  })
})

describe('useAppStore — sessions', () => {
  const session = { id: 1, title: 'Test', document_id: null, media_file_id: null, created_at: '', messages: [] }

  it('setSessions replaces list', () => {
    useAppStore.getState().setSessions([session])
    expect(useAppStore.getState().sessions).toHaveLength(1)
  })

  it('setActiveSession sets session', () => {
    useAppStore.getState().setActiveSession(session)
    expect(useAppStore.getState().activeSession?.id).toBe(1)
  })

  it('addMessage appends to active session', () => {
    useAppStore.setState({ activeSession: { ...session, messages: [] } })
    const msg: ChatMessage = { id: 1, session_id: 1, role: 'user', content: 'hi', relevant_timestamps: null, created_at: '' }
    useAppStore.getState().addMessage(1, msg)
    expect(useAppStore.getState().activeSession?.messages).toHaveLength(1)
  })

  it('addMessage ignores wrong session', () => {
    useAppStore.setState({ activeSession: { ...session, id: 99, messages: [] } })
    const msg: ChatMessage = { id: 1, session_id: 1, role: 'user', content: 'hi', relevant_timestamps: null, created_at: '' }
    useAppStore.getState().addMessage(1, msg)
    expect(useAppStore.getState().activeSession?.messages).toHaveLength(0)
  })
})
