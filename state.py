"""Call state management for voice agent."""
import asyncio
from typing import Dict, Optional, Set
from dataclasses import dataclass, field

from stt import StreamingSTT
from llm import CollectionsAgent
from tts import ElevenLabsTTS, TwilioAudioStreamer
from config import Config


@dataclass
class CallState:
    """Per-call state management."""
    stream_sid: str
    stt_processor: StreamingSTT
    llm_agent: CollectionsAgent
    tts_engine: ElevenLabsTTS
    audio_streamer: TwilioAudioStreamer
    is_speaking: bool = False
    current_tts_task: Optional[asyncio.Task] = None
    mark_id: int = 0
    pending_marks: Set[str] = field(default_factory=set)


class CallStateManager:
    """Manages call states for active voice calls."""
    
    def __init__(self, config: Config):
        self.config = config
        self._call_states: Dict[str, CallState] = {}
    
    def get_or_create(self, stream_sid: str) -> CallState:
        """Get existing call state or create a new one."""
        if stream_sid not in self._call_states:
            self._call_states[stream_sid] = CallState(
                stream_sid=stream_sid,
                stt_processor=StreamingSTT(self.config.openai_api_key, self.config),
                llm_agent=CollectionsAgent(self.config.openai_api_key, self.config),
                tts_engine=ElevenLabsTTS(self.config.elevenlabs_api_key, self.config),
                audio_streamer=TwilioAudioStreamer(self.config)
            )
        return self._call_states[stream_sid]
    
    def get(self, stream_sid: str) -> Optional[CallState]:
        """Get call state if it exists."""
        return self._call_states.get(stream_sid)
    
    def exists(self, stream_sid: str) -> bool:
        """Check if a call state exists."""
        return stream_sid in self._call_states
    
    def remove(self, stream_sid: str) -> None:
        """Remove call state and cleanup resources."""
        if stream_sid in self._call_states:
            call_state = self._call_states[stream_sid]
            # Cancel any running TTS task
            if call_state.current_tts_task and not call_state.current_tts_task.done():
                call_state.current_tts_task.cancel()
            # Reset LLM conversation history for this call
            call_state.llm_agent.reset_history()
            # Cleanup STT stream state
            call_state.stt_processor.cleanup_stream_state(stream_sid)
            del self._call_states[stream_sid]
