"""Pydantic schemas for API and WebSocket payloads."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class TwilioMessageBase(BaseModel):
    """Base for Twilio Media Streams WebSocket messages."""

    event: str
    streamSid: Optional[str] = Field(None, alias="streamSid")

    class Config:
        populate_by_name = True
        extra = "allow"  # Allow additional Twilio payload fields


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


def parse_twilio_message(data: dict) -> TwilioMessageBase:
    """Parse raw WebSocket JSON into a typed message (event + streamSid)."""
    return TwilioMessageBase(**data)
