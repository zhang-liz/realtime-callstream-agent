import asyncio
import io
import json
import base64
import uuid
from typing import AsyncGenerator, Optional
import httpx
from pydub import AudioSegment
import numpy as np
import structlog

logger = structlog.get_logger()

class ElevenLabsTTS:
    """ElevenLabs streaming TTS with mu-law conversion"""

    def __init__(self, api_key: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):  # Default: Rachel voice
        self.api_key = api_key
        self.voice_id = voice_id
        self.base_url = "https://api.elevenlabs.io/v1"

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
            # Return empty generator on error
            return

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
            return None

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

    def __init__(self):
        self.chunk_size = 320  # 20ms of 8kHz audio (160 samples per channel * 2 bytes, but mu-law is 1 byte per sample)

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
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": encoded_audio
                            }
                        }

                        await websocket.send_text(json.dumps(media_message))

                        # Small delay to prevent overwhelming the WebSocket
                        await asyncio.sleep(0.01)

            # Send mark message to indicate completion
            mark_message = {
                "event": "mark",
                "streamSid": stream_sid,
                "mark": {
                    "name": mark_id
                }
            }

            await websocket.send_text(json.dumps(mark_message))
            logger.info("TTS streaming completed", stream_sid=stream_sid, mark_id=mark_id)

        except Exception as e:
            logger.error("Audio streaming failed",
                        stream_sid=stream_sid,
                        error=str(e))
