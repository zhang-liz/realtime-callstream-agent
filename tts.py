import asyncio
import io
import json
import base64
from typing import AsyncGenerator, Optional
import httpx
from pydub import AudioSegment
import numpy as np

from exceptions import TTSError, AudioProcessingError
from config import Config
from core.logging import get_logger
from core.constants import EVENT_KEY, STREAM_SID_KEY, MEDIA_KEY, PAYLOAD_KEY, MARK_KEY, MARK_NAME_KEY

logger = get_logger()


class ElevenLabsTTS:
    """ElevenLabs streaming TTS with mu-law conversion"""

    def __init__(self, api_key: str, config: Config):
        self.api_key = api_key
        self.voice_id = config.elevenlabs_voice_id
        self.base_url = "https://api.elevenlabs.io/v1"
        self.config = config

    async def generate_speech_stream(self, text: str, stream_sid: str) -> AsyncGenerator[bytes, None]:
        """
        Generate streaming TTS and yield mu-law audio chunks
        """
        url = f"{self.base_url}/text-to-speech/{self.voice_id}/stream"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()

                    # Process audio stream in chunks
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            # Convert MP3 chunk to mu-law
                            mulaw_chunk = await self._convert_to_mulaw(chunk)
                            if mulaw_chunk:
                                yield mulaw_chunk

        except Exception as e:
            logger.error("ElevenLabs TTS failed",
                        stream_sid=stream_sid,
                        error=str(e))
            raise TTSError(f"Failed to generate TTS: {e}") from e

    async def _convert_to_mulaw(self, audio_data: bytes) -> Optional[bytes]:
        """Convert audio data to mu-law format required by Twilio"""
        try:
            # Load audio with pydub (handles various formats)
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")

            # Convert to 8kHz mono
            audio = audio.set_frame_rate(8000).set_channels(1)

            # Convert to raw PCM data
            pcm_data = np.array(audio.get_array_of_samples())

            # Apply mu-law compression
            mulaw_data = self._pcm_to_mulaw(pcm_data)

            return bytes(mulaw_data)

        except Exception as e:
            logger.error("Audio conversion failed", error=str(e))
            raise AudioProcessingError(f"Failed to convert audio to mu-law: {e}") from e

    def _pcm_to_mulaw(self, pcm_data: np.ndarray) -> np.ndarray:
        """Convert 16-bit PCM to 8-bit mu-law"""
        # Normalize to [-1, 1]
        pcm_float = pcm_data.astype(np.float32) / 32768.0

        # Mu-law compression
        mu = 255.0
        sign = np.sign(pcm_float)
        magnitude = np.abs(pcm_float)

        # Apply mu-law formula
        compressed = np.log(1.0 + mu * magnitude) / np.log(1.0 + mu)

        # Scale to 8-bit range and add sign
        mulaw = sign * compressed * 127.0 + 128.0

        # Clip and convert to uint8
        mulaw = np.clip(mulaw, 0, 255).astype(np.uint8)

        return mulaw

class TwilioAudioStreamer:
    """Handle streaming audio to Twilio WebSocket"""

    def __init__(self, config: Config):
        self.chunk_size = config.tts_chunk_size

    async def stream_to_twilio(self, websocket, tts_generator: AsyncGenerator[bytes, None], stream_sid: str, mark_id: str):
        """Stream TTS audio chunks to Twilio WebSocket"""
        try:
            async for audio_chunk in tts_generator:
                # Split into smaller chunks for real-time streaming
                for i in range(0, len(audio_chunk), self.chunk_size):
                    chunk = audio_chunk[i:i + self.chunk_size]
                    if chunk:
                        # Base64 encode
                        encoded_audio = base64.b64encode(chunk).decode('utf-8')

                        # Send media message
                        media_message = {
                            EVENT_KEY: "media",
                            STREAM_SID_KEY: stream_sid,
                            MEDIA_KEY: {PAYLOAD_KEY: encoded_audio},
                        }
                        await websocket.send_text(json.dumps(media_message))

                        # Small delay to prevent overwhelming the WebSocket
                        await asyncio.sleep(0.01)

            # Send mark message to indicate completion
            mark_message = {
                EVENT_KEY: "mark",
                STREAM_SID_KEY: stream_sid,
                MARK_KEY: {MARK_NAME_KEY: mark_id},
            }
            await websocket.send_text(json.dumps(mark_message))
            logger.info("TTS streaming completed", stream_sid=stream_sid, mark_id=mark_id)

        except Exception as e:
            logger.error("Audio streaming failed",
                        stream_sid=stream_sid,
                        error=str(e))
