"""Custom exceptions for the voice agent application."""

__all__ = [
    "VoiceAgentException",
    "ConfigurationError",
    "TwilioValidationError",
    "STTError",
    "LLMError",
    "TTSError",
    "AudioProcessingError",
]


class VoiceAgentException(Exception):
    """Base exception for voice agent errors."""
    pass


class ConfigurationError(VoiceAgentException):
    """Raised when configuration is invalid or missing."""
    pass


class TwilioValidationError(VoiceAgentException):
    """Raised when Twilio signature validation fails."""
    pass


class STTError(VoiceAgentException):
    """Raised when speech-to-text processing fails."""
    pass


class LLMError(VoiceAgentException):
    """Raised when LLM processing fails."""
    pass


class TTSError(VoiceAgentException):
    """Raised when text-to-speech processing fails."""
    pass


class AudioProcessingError(VoiceAgentException):
    """Raised when audio processing fails."""
    pass
