import { useState, useRef, useEffect } from 'react'
import { ArrowLeft, Send, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useAppStore } from '../store'
import { chatApi } from '../services/api'
import TimestampList from './TimestampList'
import type { ChatMessage, TimestampRef } from '../types'

interface Props {
  onBack: () => void
}

export default function ChatInterface({ onBack }: Props) {
  const { activeSession, addMessage, appendStreamChunk, setStreaming, clearStream, streamingMessage, isStreaming } = useAppStore()
  const [input, setInput] = useState('')
  const [seekTo, setSeekTo] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeSession?.messages, streamingMessage])

  if (!activeSession) return null

  const hasMedia = !!activeSession.media_file_id

  const sendMessage = async () => {
    const msg = input.trim()
    if (!msg || isStreaming) return
    setInput('')

    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      session_id: activeSession.id,
      role: 'user',
      content: msg,
      relevant_timestamps: null,
      created_at: new Date().toISOString(),
    }
    addMessage(activeSession.id, tempUserMsg)
    setStreaming(true)
    clearStream()

    try {
      let collectedTimestamps: TimestampRef[] = []

      await chatApi.sendMessageStream(
        { session_id: activeSession.id, message: msg, stream: true },
        (chunk) => appendStreamChunk(chunk),
        (ts) => { collectedTimestamps = ts as TimestampRef[] },
        (msgId) => {
          clearStream()
          // Reload session to get the saved message
          chatApi.getSession(activeSession.id).then(({ data }) => {
            useAppStore.setState({ activeSession: data })
          })
          setStreaming(false)
        }
      )
    } catch {
      setStreaming(false)
      clearStream()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 px-4 py-3 flex items-center gap-3">
        <button onClick={onBack} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h2 className="font-semibold text-gray-900 text-sm">{activeSession.title}</h2>
          <p className="text-xs text-gray-400">
            {activeSession.document_id ? 'PDF document' : activeSession.media_file_id ? 'Media file' : 'General chat'}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {activeSession.messages.length === 0 && !isStreaming && (
          <div className="text-center text-gray-400 text-sm mt-12">
            <p className="text-2xl mb-2">💬</p>
            <p>Ask anything about your {activeSession.document_id ? 'document' : 'media file'}</p>
          </div>
        )}

        {activeSession.messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onPlayTimestamp={setSeekTo}
          />
        ))}

        {/* Streaming bubble */}
        {isStreaming && streamingMessage && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex-shrink-0 flex items-center justify-center text-white text-xs font-bold">
              AI
            </div>
            <div className="flex-1 max-w-3xl">
              <div className="bg-gray-50 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800">
                <div className="prose prose-sm max-w-none streaming-cursor">
                  <ReactMarkdown>{streamingMessage}</ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
        )}

        {isStreaming && !streamingMessage && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex-shrink-0 flex items-center justify-center text-white text-xs font-bold">
              AI
            </div>
            <div className="bg-gray-50 rounded-2xl px-4 py-3">
              <Loader2 size={16} className="animate-spin text-gray-400" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
            className="input resize-none min-h-[42px] max-h-32 flex-1 text-sm"
            rows={1}
            disabled={isStreaming}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isStreaming}
            className="btn-primary px-3 py-2 flex-shrink-0"
          >
            {isStreaming ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({
  message,
  onPlayTimestamp,
}: {
  message: ChatMessage
  onPlayTimestamp: (start: number) => void
}) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-xl bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-blue-600 flex-shrink-0 flex items-center justify-center text-white text-xs font-bold">
        AI
      </div>
      <div className="flex-1 max-w-3xl">
        <div className="bg-gray-50 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800">
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>
        {message.relevant_timestamps && message.relevant_timestamps.length > 0 && (
          <TimestampList
            timestamps={message.relevant_timestamps}
            onPlay={onPlayTimestamp}
          />
        )}
      </div>
    </div>
  )
}
