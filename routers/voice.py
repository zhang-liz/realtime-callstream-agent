"""Twilio voice webhook and TwiML."""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse
from twilio.request_validator import RequestValidator

from config import Config
from exceptions import ConfigurationError
from core.logging import get_logger

logger = get_logger()


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
    response.connect().stream(url=f"wss://{config.public_host}/media")

    logger.info("Returning TwiML response")
    return HTMLResponse(content=str(response), media_type="application/xml")
