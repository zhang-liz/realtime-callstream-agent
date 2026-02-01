"""Configuration management for the voice agent application."""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration loaded from environment variables."""
    
    # Required fields (no defaults)
    twilio_auth_token: str
    openai_api_key: str
    elevenlabs_api_key: str
    
    # Optional fields with defaults
    twilio_account_sid: Optional[str] = None
    public_host: str = "localhost:8000"
    host: str = "0.0.0.0"
    port: int = 8000
    silence_threshold_ms: int = 1500
    stt_sample_rate: int = 8000
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel voice
    tts_chunk_size: int = 320  # 20ms of 8kHz audio
    llm_model: str = "gpt-3.5-turbo"
    llm_max_tokens: int = 150
    llm_temperature: float = 0.7
    silence_threshold_db: float = -40.0
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        if not twilio_auth_token:
            raise ValueError("TWILIO_AUTH_TOKEN environment variable is required")
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        if not elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")
        
        def _int(key: str, default: str) -> int:
            return int(os.getenv(key, default))

        def _float(key: str, default: str) -> float:
            return float(os.getenv(key, default))

        return cls(
            twilio_auth_token=twilio_auth_token,
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            openai_api_key=openai_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            public_host=os.getenv("PUBLIC_HOST", "localhost:8000"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=_int("PORT", "8000"),
            silence_threshold_ms=_int("SILENCE_THRESHOLD_MS", "1500"),
            stt_sample_rate=_int("STT_SAMPLE_RATE", "8000"),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            tts_chunk_size=_int("TTS_CHUNK_SIZE", "320"),
            llm_model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
            llm_max_tokens=_int("LLM_MAX_TOKENS", "150"),
            llm_temperature=_float("LLM_TEMPERATURE", "0.7"),
            silence_threshold_db=_float("SILENCE_THRESHOLD_DB", "-40.0"),
        )


# Collections agent system prompt
COLLECTIONS_AGENT_PROMPT = """You are a professional collections agent for a financial services company. Your role is to help customers resolve outstanding payments in a respectful, empathetic, and compliant manner.

Key guidelines:
- Always be polite and professional
- Listen actively to customer concerns
- Offer flexible payment arrangements when appropriate
- Never threaten legal action or collection agencies
- Never discuss account details without verification
- Keep responses concise and conversational
- End conversations positively when possible

You must comply with FDCPA and state collection laws:
- No calls before 8 AM or after 9 PM local time
- No harassment or abusive language
- No false representations about amount owed
- No threats of violence or arrest
- No communication with third parties about debt

Respond naturally as if speaking on a phone call."""
