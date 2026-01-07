import asyncio
import base64
import io
import time
from typing import Optional, Callable, List
import numpy as np
from pydub import AudioSegment
import openai
import structlog

logger = structlog.get_logger()

class StreamingSTT:
    """Streaming Speech-to-Text with turn detection"""

    def __init__(self, api_key: str, silence_threshold_ms: int = 1500):
        self.client = openai.OpenAI(api_key=api_key)
        self.silence_threshold_ms = silence_threshold_ms
        self.sample_rate = 8000  # Twilio uses 8kHz mu-law

    async def process_audio_chunk(self, audio_data: bytes, stream_sid: str) -> Optional[str]:
        """
        Process incoming audio chunk and return transcription if utterance complete
        Returns None if still collecting audio
        """
        # Convert mu-law to linear PCM for processing
        audio_segment = self._mulaw_to_pcm(audio_data)

        # Simple silence detection (basic VAD)
        is_silent = self._is_silent(audio_segment)

        if is_silent:
            # Check if we've been silent long enough to end the utterance
            if hasattr(self, '_last_speech_time'):
                silence_duration = time.time() - self._last_speech_time
                if silence_duration >= (self.silence_threshold_ms / 1000):
                    # Utterance complete, transcribe accumulated audio
                    if hasattr(self, '_audio_buffer') and len(self._audio_buffer) > 0:
                        transcription = await self._transcribe_audio(self._audio_buffer, stream_sid)
                        # Reset buffer
                        self._audio_buffer = bytearray()
                        delattr(self, '_last_speech_time')
                        return transcription
        else:
            # Speech detected, reset silence timer
            self._last_speech_time = time.time()

            # Accumulate audio in buffer
            if not hasattr(self, '_audio_buffer'):
                self._audio_buffer = bytearray()
            self._audio_buffer.extend(audio_data)

        return None

    def _mulaw_to_pcm(self, mulaw_data: bytes) -> AudioSegment:
        """Convert mu-law audio to PCM"""
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

    def _is_silent(self, audio_segment: AudioSegment, threshold_db: float = -40.0) -> bool:
        """Simple silence detection based on RMS amplitude"""
        try:
            rms = audio_segment.rms
            if rms == 0:
                return True

            # Convert RMS to dB
            db = 20 * np.log10(rms / 32767.0)
            return db < threshold_db
        except:
            return True

    async def _transcribe_audio(self, audio_buffer: bytearray, stream_sid: str) -> Optional[str]:
        """Transcribe accumulated audio using OpenAI Whisper"""
        try:
            # Convert mu-law buffer to WAV
            audio_segment = self._mulaw_to_pcm(bytes(audio_buffer))

            # Export to WAV bytes
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            # Transcribe with Whisper
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=("audio.wav", wav_buffer, "audio/wav"),
                    response_format="text"
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
            return None
