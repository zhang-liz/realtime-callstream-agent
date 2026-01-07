# Voice Agent

A full-duplex voice agent built with Twilio Media Streams, featuring real-time speech-to-text, LLM-powered responses, and streaming text-to-speech.

## Features

- **Full-Duplex Communication**: Bidirectional audio streaming with barge-in support
- **Real-Time STT**: Streaming speech-to-text using OpenAI Whisper
- **LLM Integration**: GPT-powered collections agent with compliance constraints
- **Streaming TTS**: ElevenLabs text-to-speech with real-time audio streaming
- **Twilio Integration**: WebSocket-based Media Streams with proper TwiML setup
- **Barge-In Support**: Interrupt TTS playback when user starts speaking
- **Turn Detection**: Automatic silence-based utterance completion
- **Security**: Twilio signature validation and correlation logging

## Setup

### Prerequisites

- Python 3.9+
- Twilio account with phone number
- OpenAI API key
- ElevenLabs API key
- ngrok (for local development)
- Node.js 18+ (for testing UI)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd voice_agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment configuration:
```bash
cp .env.example .env
```

4. Configure your environment variables in `.env`:
```env
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
PUBLIC_HOST=your-ngrok-url.ngrok.io
```

### Local Development with ngrok

1. Start ngrok to expose your local server:
```bash
ngrok http 8000
```

2. Copy the ngrok HTTPS URL (e.g., `https://abc123.ngrok.io`)

3. Update your `.env` file:
```env
PUBLIC_HOST=abc123.ngrok.io
```

4. Start the FastAPI server:
```bash
python app.py
```

### Testing UI (Optional)

For local testing without Twilio phone calls, use the included Next.js testing interface:

**Quick Start (Recommended):**
```bash
./dev.sh
```

This starts both the FastAPI backend and Next.js frontend simultaneously.

**Manual Setup:**
```bash
# Terminal 1 - Backend
python app.py

# Terminal 2 - Frontend
cd voice-agent-ui
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000) to test the voice agent directly via WebSocket.

### Twilio Configuration

1. In your Twilio Console, go to Phone Numbers
2. Select your phone number
3. Under "Voice & Fax" > "A Call Comes In", set:
   - **Webhook URL**: `https://your-ngrok-url.ngrok.io/voice`
   - **HTTP Method**: POST

## Architecture

### Components

- **`app.py`**: Main FastAPI application with WebSocket handling
- **`stt.py`**: Streaming speech-to-text with turn detection
- **`llm.py`**: Collections agent LLM integration
- **`tts.py`**: ElevenLabs streaming TTS with mu-law conversion

### Audio Flow

1. **Inbound**: Twilio → WebSocket → STT → Turn Detection
2. **Processing**: Utterance Complete → LLM → Response Generation
3. **Outbound**: Response → ElevenLabs TTS → Mu-law Conversion → Twilio WebSocket

### Call State Management

Each call maintains:
- Stream SID for correlation
- STT processor instance
- LLM agent instance
- TTS engine instance
- Current TTS task (for barge-in handling)
- Pending mark messages

## API Endpoints

### POST /voice
Returns TwiML to connect the call to WebSocket Media Streams.

**Request**: Twilio webhook with call details
**Response**: TwiML with `<Connect><Stream>` element

### WebSocket /media
Handles Twilio Media Streams protocol.

**Messages**:
- `start`: Call initialization
- `media`: Inbound audio chunks (base64 mu-law)
- `stop`: Call termination
- `mark`: TTS completion confirmation

## Compliance & Security

- **FDCPA Compliance**: Collections agent follows fair debt collection practices
- **Twilio Signature Validation**: All webhooks validated against Twilio signatures
- **Correlation Logging**: All events logged with stream SID for debugging
- **Secure WebSocket**: WSS protocol for encrypted audio streaming

## Development

### Running Tests
```bash
pytest
```

### Logging
Structured logging with correlation IDs for debugging call flows.

### Monitoring
- Call state tracking
- Audio processing metrics
- Error handling and recovery

## Production Deployment

1. Deploy to a cloud platform (Heroku, AWS, etc.)
2. Use a proper domain with HTTPS/WSS certificates
3. Configure environment variables securely
4. Set up monitoring and alerting
5. Configure rate limiting and security measures

## License

MIT License
