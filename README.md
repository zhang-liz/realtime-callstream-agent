
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
