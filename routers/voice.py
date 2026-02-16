"""Twilio voice webhook and TwiML."""

import re
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse
from twilio.request_validator import RequestValidator

from config import Config
from exceptions import ConfigurationError
from core.logging import get_logger

logger = get_logger()

# Strip optional scheme and path so we always build wss://host/media ourselves
_HOST_STRIP = re.compile(r"^(?://|https?://|wss?://)?([^/]+).*$")


def normalize_media_stream_url(public_host: str, path: str = "/media") -> str:
    """Build a wss:// URL for Twilio Media Streams from PUBLIC_HOST.
    Tolerates PUBLIC_HOST with or without scheme (e.g. https://example.com or example.com).
    """
    if not public_host or not public_host.strip():
        return f"wss://localhost:8000{path}"
    host = public_host.strip()
    match = _HOST_STRIP.match(host)
    if match:
        host = match.group(1).rstrip("/")
    if not host:
        return f"wss://localhost:8000{path}"
    return f"wss://{host}{path}"


def get_config() -> Config:
    """Dependency that returns app config. Overridden in app with actual config."""
    raise ConfigurationError("Config not injected")  # pragma: no cover


def get_validator(config: Config) -> RequestValidator:
    """Return Twilio request validator for the given config."""
    return RequestValidator(config.twilio_auth_token)


router = APIRouter(tags=["voice"])


@router.post("/voice")
async def voice_webhook(
    request: Request,
    config: Config = Depends(get_config),
) -> HTMLResponse:
    """Handle incoming voice calls from Twilio; return TwiML to connect to WebSocket."""
    logger.info("Received voice webhook", path="/voice")

    validator = get_validator(config)
    url = str(request.url)
    body = await request.body()
    signature = request.headers.get("X-Twilio-Signature")

    if not validator.validate(url, body, signature or ""):
        logger.warning("Invalid Twilio signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    response = VoiceResponse()
    stream_url = normalize_media_stream_url(config.public_host)
    response.connect().stream(url=stream_url)

    logger.info("Returning TwiML response")
    return HTMLResponse(content=str(response), media_type="application/xml")
