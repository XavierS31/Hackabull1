import asyncio
from typing import Any

from fastapi import WebSocket


class BroadcastHub:
    """Fan-out hub for three channels: thinking (JSON), status (JSON), voice (binary audio)."""

    def __init__(self):
        self.thinking_clients: set[WebSocket] = set()
        self.status_clients: set[WebSocket] = set()
        self.voice_clients: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def subscribe(self, socket: WebSocket, channel: str) -> None:
        await socket.accept()
        async with self.lock:
            if channel == "thinking":
                self.thinking_clients.add(socket)
            elif channel == "voice":
                self.voice_clients.add(socket)
            else:
                self.status_clients.add(socket)

    async def unsubscribe(self, socket: WebSocket, channel: str) -> None:
        async with self.lock:
            if channel == "thinking":
                self.thinking_clients.discard(socket)
            elif channel == "voice":
                self.voice_clients.discard(socket)
            else:
                self.status_clients.discard(socket)

    async def broadcast(self, channel: str, payload: dict[str, Any]) -> None:
        """Push a JSON payload to all clients on the given channel."""
        async with self.lock:
            targets = list(
                self.thinking_clients if channel == "thinking" else self.status_clients
            )
        for socket in targets:
            try:
                await socket.send_json(payload)
            except Exception:
                await self.unsubscribe(socket, channel)

    async def broadcast_audio(self, audio_bytes: bytes) -> None:
        """Push raw MP3 bytes to all subscribed voice clients (TTS push alerts)."""
        async with self.lock:
            targets = list(self.voice_clients)
        for socket in targets:
            try:
                await socket.send_bytes(audio_bytes)
            except Exception:
                await self.unsubscribe(socket, "voice")
