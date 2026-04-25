import axios from 'axios'

const API_BASE = '/api/v1'

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth
export const authApi = {
  register: (data: { email: string; username: string; password: string }) =>
    api.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
}

// Documents
export const documentsApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list: () => api.get('/documents/'),
  get: (id: number) => api.get(`/documents/${id}`),
  delete: (id: number) => api.delete(`/documents/${id}`),
}

// Media
export const mediaApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/media/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list: () => api.get('/media/'),
  get: (id: number) => api.get(`/media/${id}`),
  delete: (id: number) => api.delete(`/media/${id}`),
}

// Chat
export const chatApi = {
  createSession: (data: { document_id?: number; media_file_id?: number; title?: string }) =>
    api.post('/chat/sessions', data),
  listSessions: () => api.get('/chat/sessions'),
  getSession: (id: number) => api.get(`/chat/sessions/${id}`),
  deleteSession: (id: number) => api.delete(`/chat/sessions/${id}`),
  sendMessage: (data: { session_id: number; message: string; stream?: boolean }) =>
    api.post('/chat/message', data),
  sendMessageStream: (
    data: { session_id: number; message: string; stream: boolean },
    onChunk: (chunk: string) => void,
    onTimestamps: (ts: unknown[]) => void,
    onDone: (msgId: number) => void
  ): Promise<void> => {
    const token = localStorage.getItem('access_token')
    return fetch(`${API_BASE}/chat/message/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    }).then(async (res) => {
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        const lines = text.split('\n\n').filter((l) => l.startsWith('data:'))
        for (const line of lines) {
          try {
            const json = JSON.parse(line.replace('data: ', ''))
            if (json.type === 'content') onChunk(json.data)
            if (json.type === 'timestamps') onTimestamps(json.data)
            if (json.type === 'done') onDone(json.message_id)
          } catch {}
        }
      }
    })
  },
}
