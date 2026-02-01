"""WebSocket message handlers for Twilio Media Streams."""
import json
import base64
import asyncio
from typing import Any

from fastapi import WebSocket

from core.constants import (
    STREAM_SID_KEY,
    MEDIA_KEY,
    PAYLOAD_KEY,
    MARK_KEY,
    MARK_NAME_KEY,
    ACCOUNT_SID_KEY,
    SEQUENCE_NUMBER_KEY,
    TwilioEvent,
)
from core.logging import get_logger
from state import CallState
from exceptions import AudioProcessingError, STTError, LLMError, TTSError

logger = get_logger()

# Fallback message when LLM fails
LLM_FALLBACK_MESSAGE = (
    "I'm sorry, I'm having trouble processing your request. Can you please try again?"
)


async def handle_start(websocket: WebSocket, data: dict[str, Any], call_state: CallState) -> None:
    """Handle stream start event."""
    logger.info(
        "Stream started",
        stream_sid=call_state.stream_sid,
        account_sid=data.get(ACCOUNT_SID_KEY),
    )


async def handle_media(websocket: WebSocket, data: dict[str, Any], call_state: CallState) -> None:
    """Handle inbound media."""
    logger.debug(
        "Received media",
        stream_sid=call_state.stream_sid,
        sequence_number=data.get(SEQUENCE_NUMBER_KEY),
    )

    # Check for barge-in: if user is speaking while TTS is playing, stop TTS
    if call_state.current_tts_task and not call_state.current_tts_task.done():
        clear_message = {
            EVENT_KEY: TwilioEvent.CLEAR,
            STREAM_SID_KEY: call_state.stream_sid,
        }
        await websocket.send_text(json.dumps(clear_message))

        # Cancel current TTS task
        call_state.current_tts_task.cancel()
        try:
            await call_state.current_tts_task
        except asyncio.CancelledError:
            pass

        logger.info("Barge-in detected, stopped current TTS",
                   stream_sid=call_state.stream_sid)

    # Decode base64 audio
    try:
        media = data.get(MEDIA_KEY) or {}
        audio_payload = media.get(PAYLOAD_KEY)
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
            try:
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
            except LLMError as e:
                logger.error(
                    "LLM response generation failed",
                    stream_sid=call_state.stream_sid,
                    error=str(e),
                )
                call_state.mark_id += 1
                mark_id = f"mark_{call_state.mark_id}"
                call_state.current_tts_task = asyncio.create_task(
                    stream_tts_response(websocket, call_state, LLM_FALLBACK_MESSAGE, mark_id)
                )

    except (AudioProcessingError, STTError) as e:
        logger.error("Media processing failed",
                    stream_sid=call_state.stream_sid,
                    error=str(e))
    except Exception as e:
        logger.error("Unexpected error in media handling",
                    stream_sid=call_state.stream_sid,
                    error=str(e))


async def handle_stop(websocket: WebSocket, data: dict[str, Any], call_state: CallState) -> None:
    """Handle stream stop event."""
    logger.info("Stream stopped", stream_sid=call_state.stream_sid)


async def handle_mark(websocket: WebSocket, data: dict[str, Any], call_state: CallState) -> None:
    """Handle mark event (TTS playback completed)."""
    mark_obj = data.get(MARK_KEY) or {}
    mark_name = mark_obj.get(MARK_NAME_KEY) or data.get(MARK_NAME_KEY)
    if mark_name and mark_name in call_state.pending_marks:
        call_state.pending_marks.discard(mark_name)

    logger.info(
        "Mark received",
        stream_sid=call_state.stream_sid,
        mark_name=mark_name,
    )


async def stream_tts_response(
    websocket: WebSocket,
    call_state: CallState,
    text: str,
    mark_id: str
) -> None:
    """Stream TTS response to Twilio."""
    try:
        # Add mark to pending set
        call_state.pending_marks.add(mark_id)

        # Generate TTS stream
        tts_stream = call_state.tts_engine.generate_speech_stream(
            text, call_state.stream_sid
        )

        # Stream to Twilio
        await call_state.audio_streamer.stream_to_twilio(
            websocket, tts_stream, call_state.stream_sid, mark_id
        )

        logger.info("TTS streaming task completed",
                   stream_sid=call_state.stream_sid,
                   mark_id=mark_id)

    except (TTSError, AudioProcessingError) as e:
        logger.error("TTS streaming failed",
                    stream_sid=call_state.stream_sid,
                    mark_id=mark_id,
                    error=str(e))
    except Exception as e:
        logger.error("Unexpected error in TTS streaming",
                    stream_sid=call_state.stream_sid,
                    mark_id=mark_id,
                    error=str(e))
