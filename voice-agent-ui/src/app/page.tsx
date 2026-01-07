'use client'

import { useState, useRef, useEffect } from 'react'
import VoiceAgentInterface from '../components/VoiceAgentInterface'

export default function Home() {
  return (
    <main className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-800">
          Voice Agent Test Interface
        </h1>
        <p className="text-center text-gray-600 mb-8">
          Test your full-duplex voice agent with real-time speech recognition and text-to-speech
        </p>
        <VoiceAgentInterface />
      </div>
    </main>
  )
}
