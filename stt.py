import asyncio
import io
import time
from typing import Optional, Dict
import numpy as np
from pydub import AudioSegment
import openai

from exceptions import STTError, AudioProcessingError
from config import Config
from core.logging import get_logger

logger = get_logger()


class StreamState:
    """State for a single audio stream."""
    
    def __init__(self):
        self.audio_buffer = bytearray()
        self.last_speech_time: Optional[float] = None


class StreamingSTT:
    """Streaming Speech-to-Text with turn detection"""

    def __init__(self, api_key: str, config: Config):
        self.client = openai.OpenAI(api_key=api_key)
        self.silence_threshold_ms = config.silence_threshold_ms
        self.sample_rate = config.stt_sample_rate
        self.silence_threshold_db = config.silence_threshold_db
        # Per-stream state management
        self._stream_states: Dict[str, StreamState] = {}

    def _get_stream_state(self, stream_sid: str) -> StreamState:
        """Get or create state for a stream."""
        if stream_sid not in self._stream_states:
            self._stream_states[stream_sid] = StreamState()
        return self._stream_states[stream_sid]

    def cleanup_stream_state(self, stream_sid: str) -> None:
        """Clean up state for a stream. Call when call ends."""
        if stream_sid in self._stream_states:
            del self._stream_states[stream_sid]

    async def process_audio_chunk(self, audio_data: bytes, stream_sid: str) -> Optional[str]:
        """
        Process incoming audio chunk and return transcription if utterance complete.
        Returns None if still collecting audio.
        """
        stream_state = self._get_stream_state(stream_sid)
        
        try:
            # Convert mu-law to linear PCM for processing
            audio_segment = self._mulaw_to_pcm(audio_data)

            # Simple silence detection (basic VAD)
            is_silent = self._is_silent(audio_segment)

            if is_silent:
                # Check if we've been silent long enough to end the utterance
                if stream_state.last_speech_time is not None:
                    silence_duration = time.time() - stream_state.last_speech_time
                    if silence_duration >= (self.silence_threshold_ms / 1000):
                        # Utterance complete, transcribe accumulated audio
                        if len(stream_state.audio_buffer) > 0:
                            transcription = await self._transcribe_audio(
                                stream_state.audio_buffer, stream_sid
                            )
                            # Reset buffer
                            stream_state.audio_buffer = bytearray()
                            stream_state.last_speech_time = None
                            return transcription
            else:
                # Speech detected, reset silence timer
                stream_state.last_speech_time = time.time()
                # Accumulate audio in buffer
                stream_state.audio_buffer.extend(audio_data)

            return None
        except Exception as e:
            logger.error("Audio chunk processing failed",
                        stream_sid=stream_sid,
                        error=str(e))
            raise AudioProcessingError(f"Failed to process audio chunk: {e}") from e

    def _mulaw_to_pcm(self, mulaw_data: bytes) -> AudioSegment:
        """Convert mu-law audio to PCM."""
        try:
            # Convert mu-law bytes to numpy array
            mulaw_array = np.frombuffer(mulaw_data, dtype=np.uint8)

            # Mu-law to linear conversion
            # mu-law formula: y = sign(x) * (2^8) * ln(1 + μ| x |) / ln(1 + μ)
            # where μ = 255 for standard mu-law
            mu = 255.0
            linear = np.sign(mulaw_array - 128) * (1.0 / mu) * ((1.0 + mu) ** np.abs(mulaw_array - 128) - 1.0)
            linear = linear * 32767  # Scale to 16-bit

            # Convert to AudioSegment
            pcm_data = linear.astype(np.int16).tobytes()
            return AudioSegment(pcm_data, frame_rate=self.sample_rate, sample_width=2, channels=1)
        except Exception as e:
            logger.error("Mu-law to PCM conversion failed", error=str(e))
            raise AudioProcessingError(f"Failed to convert mu-law to PCM: {e}") from e

    def _is_silent(self, audio_segment: AudioSegment) -> bool:
        """Simple silence detection based on RMS amplitude."""
        try:
            rms = audio_segment.rms
            if rms == 0:
                return True

            # Convert RMS to dB
            db = 20 * np.log10(rms / 32767.0)
            return db < self.silence_threshold_db
        except Exception:
            return True

    async def _transcribe_audio(self, audio_buffer: bytearray, stream_sid: str) -> Optional[str]:
        """Transcribe accumulated audio using OpenAI Whisper."""
        try:
            # Convert mu-law buffer to WAV
            audio_segment = self._mulaw_to_pcm(bytes(audio_buffer))

            # Export to WAV bytes
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            # Transcribe with Whisper (run sync API in thread pool)
            response = await asyncio.to_thread(
                lambda: self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=("audio.wav", wav_buffer, "audio/wav"),
                    response_format="text",
                )
            )

            transcription = response.strip()
            logger.info("Transcription completed",
                       stream_sid=stream_sid,
                       transcription_length=len(transcription))

            return transcription if transcription else None

        except Exception as e:
            logger.error("Transcription failed",
                        stream_sid=stream_sid,
                        error=str(e))
            raise STTError(f"Failed to transcribe audio: {e}") from e
