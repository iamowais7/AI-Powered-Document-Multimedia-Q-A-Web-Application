export interface User {
  id: number
  email: string
  username: string
  is_active: boolean
  created_at: string
}

export interface AuthToken {
  access_token: string
  token_type: string
  user: User
}

export interface Document {
  id: number
  filename: string
  original_filename: string
  file_size: number
  content_type: string
  extracted_text: string | null
  summary: string | null
  page_count: number | null
  created_at: string
}

export interface TranscriptSegment {
  start: number
  end: number
  text: string
}

export interface MediaFile {
  id: number
  filename: string
  original_filename: string
  file_size: number
  content_type: string
  media_type: 'audio' | 'video'
  duration: number | null
  transcription: string | null
  summary: string | null
  segments: TranscriptSegment[] | null
  created_at: string
}

export interface TimestampRef {
  start: number
  end: number
  text: string
  relevance_score: number
}

export interface ChatMessage {
  id: number
  session_id: number
  role: 'user' | 'assistant'
  content: string
  relevant_timestamps: TimestampRef[] | null
  created_at: string
}

export interface ChatSession {
  id: number
  title: string
  document_id: number | null
  media_file_id: number | null
  created_at: string
  messages: ChatMessage[]
}

export interface ChatResponse {
  message: ChatMessage
  relevant_timestamps: TimestampRef[] | null
}

export type UploadType = 'document' | 'audio' | 'video'
