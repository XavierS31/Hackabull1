import asyncio

import httpx
from elevenlabs.client import ElevenLabs


class VoiceService:
    """Wraps ElevenLabs TTS (SDK) and STT (REST API)."""

    def __init__(self, api_key: str, voice_id: str, model_id: str):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self._client = ElevenLabs(api_key=api_key)

    # ---------- TTS ----------

    def synthesize(self, text: str) -> bytes:
        """Blocking: text → MP3 bytes via ElevenLabs SDK."""
        chunks = self._client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            model_id=self.model_id,
        )
        return b"".join(chunks)

    async def synthesize_async(self, text: str) -> bytes:
        """Non-blocking wrapper around synthesize() for use inside async handlers."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.synthesize, text)

    # ---------- STT ----------

    async def transcribe_async(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Non-blocking: audio bytes → transcript text via ElevenLabs Scribe REST API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": self.api_key},
                files={"file": (filename, audio_bytes, "audio/webm")},
                data={"model_id": "scribe_v1"},
            )
            if resp.status_code != 200:
                return ""
            return resp.json().get("text", "")
