"""Application constants."""


class TwilioEvent:
    """Twilio Media Streams WebSocket event type names."""

    START = "start"
    MEDIA = "media"
    STOP = "stop"
    MARK = "mark"
    CLEAR = "clear"


# Twilio message payload keys
STREAM_SID_KEY = "streamSid"
EVENT_KEY = "event"
MEDIA_KEY = "media"
PAYLOAD_KEY = "payload"
MARK_KEY = "mark"
MARK_NAME_KEY = "name"
ACCOUNT_SID_KEY = "accountSid"
SEQUENCE_NUMBER_KEY = "sequenceNumber"
