"""Twilio Media Streams WebSocket."""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from state import CallStateManager
from core.logging import get_logger
from core.constants import TwilioEvent, STREAM_SID_KEY, EVENT_KEY

from handlers import handle_start, handle_media, handle_stop, handle_mark

logger = get_logger()

router = APIRouter(tags=["media"])


@router.websocket("/media")
async def media_websocket(
    websocket: WebSocket,
) -> None:
    """Handle Twilio Media Streams WebSocket. Requires app.state.call_state_manager."""
    await websocket.accept()
    stream_sid: str | None = None
    call_state_manager: CallStateManager = websocket.app.state.call_state_manager

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            msg_type = data.get(EVENT_KEY)
            stream_sid = data.get(STREAM_SID_KEY)

            if not stream_sid:
                logger.warning("No streamSid in message", message=data)
                continue

            was_new = not call_state_manager.exists(stream_sid)
            call_state = call_state_manager.get_or_create(stream_sid)
            if was_new:
                logger.info("New call started", stream_sid=stream_sid)

            if msg_type == TwilioEvent.START:
                await handle_start(websocket, data, call_state)
            elif msg_type == TwilioEvent.MEDIA:
                await handle_media(websocket, data, call_state)
            elif msg_type == TwilioEvent.STOP:
                await handle_stop(websocket, data, call_state)
            elif msg_type == TwilioEvent.MARK:
                await handle_mark(websocket, data, call_state)
            else:
                logger.warning(
                    "Unknown message type",
                    type=msg_type,
                    stream_sid=stream_sid,
                )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", stream_sid=stream_sid)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), stream_sid=stream_sid)
    finally:
        if stream_sid:
            call_state_manager.remove(stream_sid)
