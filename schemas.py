"""Pydantic schemas for API and WebSocket payloads."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TwilioMessageBase(BaseModel):
    """Base for Twilio Media Streams WebSocket messages."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    event: str
    streamSid: Optional[str] = Field(None, alias="streamSid")


class TwilioStartPayload(TwilioMessageBase):
    """Payload for 'start' event."""

    event: str = "start"
    accountSid: Optional[str] = Field(None, alias="accountSid")


class TwilioMediaPayload(TwilioMessageBase):
    """Payload for 'media' event."""

    event: str = "media"
    sequenceNumber: Optional[str] = Field(None, alias="sequenceNumber")
    media: Optional[dict[str, Any]] = None


class TwilioMarkPayload(TwilioMessageBase):
    """Payload for 'mark' event."""

    event: str = "mark"
    mark: Optional[dict[str, Any]] = None


class TwilioStopPayload(TwilioMessageBase):
    """Payload for 'stop' event."""

    event: str = "stop"


def parse_twilio_message(data: dict) -> TwilioMessageBase:
    """Parse raw WebSocket JSON into a typed message (event + streamSid)."""
    return TwilioMessageBase(**data)
