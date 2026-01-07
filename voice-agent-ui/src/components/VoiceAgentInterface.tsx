'use client'

import { useState, useRef, useEffect, useCallback } from 'react'

interface Message {
  id: string
  type: 'user' | 'agent' | 'system'
  content: string
  timestamp: Date
}

interface CallState {
  isConnected: boolean
  isRecording: boolean
  isPlaying: boolean
  streamSid: string | null
}

export default function VoiceAgentInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [callState, setCallState] = useState<CallState>({
    isConnected: false,
    isRecording: false,
    isPlaying: false,
    streamSid: null
  })
  const [serverUrl, setServerUrl] = useState('ws://localhost:8000/media')
  const [isConnecting, setIsConnecting] = useState(false)

  const websocketRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioChunksRef = useRef<Float32Array[]>([])
  const sequenceNumberRef = useRef(0)

  const addMessage = useCallback((type: Message['type'], content: string) => {
    const message: Message = {
      id: Date.now().toString(),
      type,
      content,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, message])
  }, [])

  const connectToServer = useCallback(async () => {
    if (callState.isConnected) return

    setIsConnecting(true)
    addMessage('system', 'Connecting to voice agent...')

    try {
      const ws = new WebSocket(serverUrl)
      websocketRef.current = ws

      ws.onopen = () => {
        setIsConnecting(false)
        setCallState(prev => ({ ...prev, isConnected: true }))
        addMessage('system', 'Connected to voice agent')

        // Send start message (simulating Twilio start)
        const streamSid = `test-${Date.now()}`
        setCallState(prev => ({ ...prev, streamSid }))
        ws.send(JSON.stringify({
          event: 'start',
          streamSid,
          accountSid: 'test-account',
          callSid: 'test-call'
        }))
      }

      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data)

        if (data.event === 'media') {
          // Handle incoming audio from agent
          await playAudioFromBase64(data.media.payload)
        } else if (data.event === 'mark') {
          addMessage('system', `TTS playback completed (mark: ${data.mark.name})`)
        }
      }

      ws.onclose = () => {
        setCallState(prev => ({
          ...prev,
          isConnected: false,
          isRecording: false,
          streamSid: null
        }))
        addMessage('system', 'Disconnected from voice agent')
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        addMessage('system', 'Connection error')
        setIsConnecting(false)
      }

    } catch (error) {
      console.error('Connection failed:', error)
      addMessage('system', 'Failed to connect')
      setIsConnecting(false)
    }
  }, [callState.isConnected, serverUrl, addMessage])

  const disconnectFromServer = useCallback(() => {
    if (websocketRef.current) {
      websocketRef.current.close()
    }
    stopRecording()
  }, [])

  const startRecording = useCallback(async () => {
    if (!callState.isConnected || callState.isRecording) return

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // Set up audio processing
      audioContextRef.current = new AudioContext({ sampleRate: 8000 })
      const source = audioContextRef.current.createMediaStreamSource(stream)
      const processor = audioContextRef.current.createScriptProcessor(1024, 1, 1)

      processor.onaudioprocess = (event) => {
        const inputBuffer = event.inputBuffer
        const inputData = inputBuffer.getChannelData(0)

        // Convert to 16-bit PCM
        const pcm16 = new Int16Array(inputData.length)
        for (let i = 0; i < inputData.length; i++) {
          pcm16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768))
        }

        // Convert to mu-law (simplified)
        const mulaw = new Uint8Array(pcm16.length)
        for (let i = 0; i < pcm16.length; i++) {
          const sample = pcm16[i]
          const sign = sample < 0 ? 0x80 : 0
          const magnitude = Math.abs(sample)
          let mulaw_val = sign | (127 - Math.floor(127 * Math.log(1 + 255 * magnitude / 32768) / Math.log(256)))
          mulaw[i] = mulaw_val
        }

        // Send to server
        if (websocketRef.current && callState.streamSid) {
          const base64Audio = btoa(String.fromCharCode(...mulaw))
          websocketRef.current.send(JSON.stringify({
            event: 'media',
            streamSid: callState.streamSid,
            media: {
              payload: base64Audio
            },
            sequenceNumber: sequenceNumberRef.current++
          }))
        }
      }

      source.connect(processor)
      processor.connect(audioContextRef.current.destination)

      setCallState(prev => ({ ...prev, isRecording: true }))
      addMessage('system', 'Started recording')

    } catch (error) {
      console.error('Failed to start recording:', error)
      addMessage('system', 'Failed to start recording')
    }
  }, [callState.isConnected, callState.isRecording, callState.streamSid])

  const stopRecording = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    setCallState(prev => ({ ...prev, isRecording: false }))
    addMessage('system', 'Stopped recording')
  }, [])

  const playAudioFromBase64 = useCallback(async (base64Audio: string) => {
    try {
      setCallState(prev => ({ ...prev, isPlaying: true }))

      // Convert base64 to binary
      const binaryString = atob(base64Audio)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }

      // Convert mu-law back to linear PCM (simplified)
      const pcm16 = new Int16Array(bytes.length)
      for (let i = 0; i < bytes.length; i++) {
        const mulaw_val = bytes[i]
        const sign = (mulaw_val & 0x80) ? -1 : 1
        const magnitude = ((mulaw_val & 0x7F) ^ 0x7F) + 1
        pcm16[i] = sign * (magnitude - 33) * 4
      }

      // Convert to float32 for Web Audio
      const float32 = new Float32Array(pcm16.length)
      for (let i = 0; i < pcm16.length; i++) {
        float32[i] = pcm16[i] / 32768
      }

      // Play audio
      const audioContext = new AudioContext({ sampleRate: 8000 })
      const buffer = audioContext.createBuffer(1, float32.length, 8000)
      buffer.copyFromChannel(float32, 0)

      const source = audioContext.createBufferSource()
      source.buffer = buffer
      source.connect(audioContext.destination)
      source.start()

      source.onended = () => {
        setCallState(prev => ({ ...prev, isPlaying: false }))
        audioContext.close()
      }

    } catch (error) {
      console.error('Failed to play audio:', error)
      setCallState(prev => ({ ...prev, isPlaying: false }))
    }
  }, [])

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Connection Controls */}
      <div className="mb-6">
        <div className="flex gap-4 mb-4">
          <input
            type="text"
            value={serverUrl}
            onChange={(e) => setServerUrl(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="WebSocket URL"
          />
          <button
            onClick={callState.isConnected ? disconnectFromServer : connectToServer}
            disabled={isConnecting}
            className={`px-4 py-2 rounded-md font-medium ${
              callState.isConnected
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-green-500 hover:bg-green-600 text-white'
            } disabled:opacity-50`}
          >
            {isConnecting ? 'Connecting...' : callState.isConnected ? 'Disconnect' : 'Connect'}
          </button>
        </div>

        <div className="flex gap-2 text-sm">
          <span className={`px-2 py-1 rounded ${
            callState.isConnected ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
          }`}>
            {callState.isConnected ? 'Connected' : 'Disconnected'}
          </span>
          <span className={`px-2 py-1 rounded ${
            callState.isRecording ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
          }`}>
            {callState.isRecording ? 'Recording' : 'Not Recording'}
          </span>
          <span className={`px-2 py-1 rounded ${
            callState.isPlaying ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
          }`}>
            {callState.isPlaying ? 'Playing' : 'Not Playing'}
          </span>
        </div>
      </div>

      {/* Voice Controls */}
      <div className="mb-6">
        <div className="flex gap-4">
          <button
            onClick={startRecording}
            disabled={!callState.isConnected || callState.isRecording}
            className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            🎤 Start Recording
          </button>
          <button
            onClick={stopRecording}
            disabled={!callState.isRecording}
            className="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ⏹️ Stop Recording
          </button>
        </div>
        <p className="text-sm text-gray-600 mt-2">
          Click "Start Recording" to begin speaking. The system will transcribe your speech and respond automatically.
        </p>
      </div>

      {/* Messages */}
      <div className="border border-gray-200 rounded-lg p-4 max-h-96 overflow-y-auto">
        <h3 className="font-semibold mb-4">Conversation</h3>
        {messages.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No messages yet. Connect and start recording to begin the conversation.
          </p>
        ) : (
          <div className="space-y-3">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`p-3 rounded-lg ${
                  message.type === 'user'
                    ? 'bg-blue-50 border-l-4 border-blue-500'
                    : message.type === 'agent'
                    ? 'bg-green-50 border-l-4 border-green-500'
                    : 'bg-gray-50 border-l-4 border-gray-500'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-medium text-sm capitalize">{message.type}</span>
                  <span className="text-xs text-gray-500">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-gray-800">{message.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
