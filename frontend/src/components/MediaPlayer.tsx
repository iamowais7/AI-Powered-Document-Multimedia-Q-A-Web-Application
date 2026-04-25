import { useRef, useEffect } from 'react'

interface Props {
  src: string
  mediaType: 'audio' | 'video'
  seekTo?: number | null
}

export default function MediaPlayer({ src, mediaType, seekTo }: Props) {
  const ref = useRef<HTMLVideoElement | HTMLAudioElement>(null)

  useEffect(() => {
    if (seekTo !== null && seekTo !== undefined && ref.current) {
      ref.current.currentTime = seekTo
      ref.current.play()
    }
  }, [seekTo])

  if (mediaType === 'video') {
    return (
      <video
        ref={ref as React.RefObject<HTMLVideoElement>}
        src={src}
        controls
        className="w-full rounded-lg max-h-48"
      />
    )
  }

  return (
    <audio
      ref={ref as React.RefObject<HTMLAudioElement>}
      src={src}
      controls
      className="w-full"
    />
  )
}
