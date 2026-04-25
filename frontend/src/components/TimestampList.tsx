import { Play } from 'lucide-react'
import type { TimestampRef } from '../types'

interface Props {
  timestamps: TimestampRef[]
  onPlay: (start: number) => void
}

export default function TimestampList({ timestamps, onPlay }: Props) {
  if (!timestamps.length) return null

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = Math.floor(secs % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="mt-3 border border-blue-100 rounded-lg overflow-hidden">
      <div className="bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700">
        Relevant timestamps
      </div>
      <div className="divide-y divide-gray-100">
        {timestamps.map((ts, i) => (
          <div key={i} className="flex items-center gap-2 px-3 py-2">
            <button
              onClick={() => onPlay(ts.start)}
              className="flex-shrink-0 w-7 h-7 bg-blue-600 hover:bg-blue-700 text-white rounded-full flex items-center justify-center transition-colors"
              title={`Play from ${formatTime(ts.start)}`}
            >
              <Play size={10} fill="white" />
            </button>
            <span className="text-xs font-mono text-blue-600 whitespace-nowrap">
              {formatTime(ts.start)} – {formatTime(ts.end)}
            </span>
            <p className="text-xs text-gray-600 truncate">{ts.text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
