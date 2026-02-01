'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
// WebSocket: used when integrating with backend /media endpoint

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected'

export default function VoiceAgentInterface() {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    if (typeof window !== 'undefined') {
      audioRef.current = new Audio()
    }
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
    }
  }, [])

  const connectToServer = useCallback(() => {
    setConnectionStatus('connecting')
    // Placeholder: in a full implementation, open WebSocket to backend /media
    setConnectionStatus('connected')
  }, [])

  const startRecording = useCallback(() => {
    // Placeholder: in a full implementation, start microphone capture and send to WebSocket
  }, [])

  const playAudioFromBase64 = useCallback((base64: string) => {
    const audio = audioRef.current
    if (!audio) return
    try {
      audio.src = `data:audio/mpeg;base64,${base64}`
      audio.play().catch(() => {})
    } catch {
      // ignore
    }
  }, [])

  const isConnected = connectionStatus === 'connected'
  const connectLabel =
    connectionStatus === 'connected'
      ? 'Connected'
      : connectionStatus === 'connecting'
        ? 'Connecting…'
        : 'Connect'

  return (
    <section
      className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
      aria-label="Voice agent controls"
    >
      <div className="flex flex-col gap-4">
        <button
          type="button"
          onClick={connectToServer}
          disabled={connectionStatus === 'connecting'}
          className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          aria-label={isConnected ? 'Connected to server' : 'Connect to voice agent server'}
          aria-pressed={isConnected}
        >
          {connectLabel}
        </button>
        <button
          type="button"
          onClick={startRecording}
          disabled={!isConnected}
          className="rounded-md border border-gray-300 px-4 py-2 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-gray-300 focus:ring-offset-2"
          aria-label="Start recording"
          aria-pressed={false}
        >
          Start Recording
        </button>
      </div>
    </section>
  )
}
