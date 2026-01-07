# Voice Agent Test UI

A Next.js web interface for testing the full-duplex voice agent locally.

## Features

- **WebSocket Connection**: Connect directly to the voice agent's WebSocket endpoint
- **Real-time Audio**: Record and play audio with proper mu-law encoding/decoding
- **Conversation Display**: View transcription and agent responses in real-time
- **Call Simulation**: Simulate Twilio Media Streams protocol for testing
- **Status Indicators**: Visual feedback for connection, recording, and playback states

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

## Usage

1. **Connect**: Enter the WebSocket URL of your voice agent (default: `ws://localhost:8000/media`)
2. **Start Recording**: Click the recording button to begin speaking
3. **Speak**: Your speech will be transcribed and sent to the voice agent
4. **Listen**: The agent's response will be played back automatically
5. **Stop**: Click stop recording when done

## Architecture

The UI simulates the Twilio Media Streams protocol:

- **Audio Processing**: Converts browser audio to mu-law format (8kHz)
- **WebSocket Communication**: Sends/receives media messages like Twilio
- **Real-time Playback**: Streams agent responses as they arrive
- **Protocol Simulation**: Handles start/stop/media/mark events

## Browser Requirements

- Modern browser with Web Audio API support
- Microphone access for recording
- WebSocket support for real-time communication

## Development

The interface is built with:
- **Next.js 14**: React framework with App Router
- **TypeScript**: Type safety and better development experience
- **Tailwind CSS**: Utility-first CSS framework
- **Web Audio API**: Real-time audio processing
