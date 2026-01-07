import os
import logging
from typing import Dict, Optional
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import json
import asyncio
from twilio.twiml.voice_response import VoiceResponse
from twilio.request_validator import RequestValidator
import structlog

from stt import StreamingSTT
from llm import CollectionsAgent
from tts import ElevenLabsTTS, TwilioAudioStreamer

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(title="Voice Agent", version="1.0.0")

# Environment variables
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "localhost:8000")

class CallState:
    """Per-call state management"""
    def __init__(self, stream_sid: str):
        self.stream_sid = stream_sid
        self.stt_processor = StreamingSTT(OPENAI_API_KEY)
        self.llm_agent = CollectionsAgent(OPENAI_API_KEY)
        self.tts_engine = ElevenLabsTTS(ELEVENLABS_API_KEY)
        self.audio_streamer = TwilioAudioStreamer()
        self.is_speaking = False
        self.current_tts_task: Optional[asyncio.Task] = None
        self.mark_id = 0
        self.pending_marks = set()  # Track pending mark messages

# Global call states
call_states: Dict[str, CallState] = {}

@app.get("/")
async def root():
    return {"message": "Voice Agent API", "status": "running"}

@app.post("/voice")
async def voice_endpoint(request: Request):
    """Handle incoming voice calls from Twilio"""
    logger.info("Received voice webhook", path="/voice")

    # Validate Twilio signature
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    url = str(request.url)
    body = await request.body()
    signature = request.headers.get('X-Twilio-Signature')

    if not validator.validate(url, body, signature):
        logger.warning("Invalid Twilio signature", signature=signature)
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Generate TwiML response
    response = VoiceResponse()
    response.connect().stream(url=f"wss://{PUBLIC_HOST}/media")

    logger.info("Returning TwiML response", twiml=str(response))
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media")
async def media_websocket(websocket: WebSocket):
    """Handle Twilio Media Streams WebSocket"""
    await websocket.accept()
    stream_sid = None

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            msg_type = data.get("event")
            stream_sid = data.get("streamSid")

            if not stream_sid:
                logger.warning("No streamSid in message", message=data)
                continue

            # Get or create call state
            if stream_sid not in call_states:
                call_states[stream_sid] = CallState(stream_sid)
                logger.info("New call started", stream_sid=stream_sid)

            call_state = call_states[stream_sid]

            if msg_type == "start":
                await handle_start(websocket, data, call_state)
            elif msg_type == "media":
                await handle_media(websocket, data, call_state)
            elif msg_type == "stop":
                await handle_stop(websocket, data, call_state)
            elif msg_type == "mark":
                await handle_mark(websocket, data, call_state)
            else:
                logger.warning("Unknown message type", type=msg_type, stream_sid=stream_sid)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", stream_sid=stream_sid)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), stream_sid=stream_sid)
    finally:
        if stream_sid and stream_sid in call_states:
            del call_states[stream_sid]

async def handle_start(websocket: WebSocket, data: dict, call_state: CallState):
    """Handle stream start event"""
    logger.info("Stream started", stream_sid=call_state.stream_sid,
                account_sid=data.get("accountSid"))

async def handle_media(websocket: WebSocket, data: dict, call_state: CallState):
    """Handle inbound media"""
    logger.debug("Received media", stream_sid=call_state.stream_sid,
                sequence_number=data.get("sequenceNumber"))

    # Check for barge-in: if user is speaking while TTS is playing, stop TTS
    if call_state.current_tts_task and not call_state.current_tts_task.done():
        # Send clear message to stop current TTS playback
        clear_message = {
            "event": "clear",
            "streamSid": call_state.stream_sid
        }
        await websocket.send_text(json.dumps(clear_message))

        # Cancel current TTS task
        call_state.current_tts_task.cancel()
        try:
            await call_state.current_tts_task
        except asyncio.CancelledError:
            pass

        logger.info("Barge-in detected, stopped current TTS", stream_sid=call_state.stream_sid)

    # Decode base64 audio
    try:
        audio_payload = data.get("media", {}).get("payload")
        if not audio_payload:
            return

        audio_data = base64.b64decode(audio_payload)

        # Process audio through STT
        transcription = await call_state.stt_processor.process_audio_chunk(
            audio_data, call_state.stream_sid
        )

        # If utterance is complete, generate response
        if transcription:
            logger.info("Utterance complete",
                       stream_sid=call_state.stream_sid,
                       transcription=transcription)

            # Generate LLM response
            llm_response = await call_state.llm_agent.generate_response(
                transcription, call_state.stream_sid
            )

            if llm_response:
                # Start TTS streaming in background
                call_state.mark_id += 1
                mark_id = f"mark_{call_state.mark_id}"

                call_state.current_tts_task = asyncio.create_task(
                    stream_tts_response(websocket, call_state, llm_response, mark_id)
                )

    except Exception as e:
        logger.error("Media processing failed",
                    stream_sid=call_state.stream_sid,
                    error=str(e))

async def handle_stop(websocket: WebSocket, data: dict, call_state: CallState):
    """Handle stream stop event"""
    logger.info("Stream stopped", stream_sid=call_state.stream_sid)

async def handle_mark(websocket: WebSocket, data: dict, call_state: CallState):
    """Handle mark event (TTS playback completed)"""
    mark_name = data.get("name")
    if mark_name in call_state.pending_marks:
        call_state.pending_marks.remove(mark_name)

    logger.info("Mark received", stream_sid=call_state.stream_sid, mark_name=mark_name)

async def stream_tts_response(websocket: WebSocket, call_state: CallState, text: str, mark_id: str):
    """Stream TTS response to Twilio"""
    try:
        # Add mark to pending set
        call_state.pending_marks.add(mark_id)

        # Generate TTS stream
        tts_stream = call_state.tts_engine.generate_speech_stream(text, call_state.stream_sid)

        # Stream to Twilio
        await call_state.audio_streamer.stream_to_twilio(
            websocket, tts_stream, call_state.stream_sid, mark_id
        )

        logger.info("TTS streaming task completed",
                   stream_sid=call_state.stream_sid,
                   mark_id=mark_id)

    except Exception as e:
        logger.error("TTS streaming failed",
                    stream_sid=call_state.stream_sid,
                    mark_id=mark_id,
                    error=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
