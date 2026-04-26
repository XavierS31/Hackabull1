import asyncio
import json
import re
from typing import Any

from google import genai
from google.genai import types
from fastapi import HTTPException

from ..config import ONBOARDING_PROMPT, settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.effective_api_key)
    return _client


def _extract_json(payload: str) -> dict[str, Any]:
    payload = payload.strip()
    if payload.startswith("{"):
        return json.loads(payload)
    match = re.search(r"\{.*\}", payload, flags=re.S)
    if not match:
        raise ValueError("No JSON object found in model response.")
    return json.loads(match.group(0))


def _build_contents(user_text: str, image_bytes: bytes | None, mime_type: str) -> list:
    parts: list[types.Part] = [types.Part(text=user_text)]
    if image_bytes:
        parts.append(
            types.Part(
                inline_data=types.Blob(mime_type=mime_type, data=image_bytes)
            )
        )
    return [types.Content(role="user", parts=parts)]


async def call_gemma_text(
    system: str,
    user_text: str,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
) -> str:
    """Call Gemma 4 with optional image. Returns plain text — never raises."""
    if not settings.effective_api_key:
        return "AI service not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY in backend/.env."

    contents = _build_contents(user_text, image_bytes, mime_type)
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.4,
    )

    try:
        client = _get_client()
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=settings.gemma_model,
                contents=contents,
                config=config,
            ),
        )
        return response.text or ""
    except Exception as exc:
        return f"[Gemma error] {exc}"


async def call_gemma_with_qr(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    """Call Gemma 4 with a QR/onboarding image; returns parsed JSON dict."""
    if not settings.effective_api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY or GOOGLE_API_KEY is missing in backend/.env.",
        )

    contents = _build_contents(
        "Parse this medical onboarding QR image and classify active agents.",
        image_bytes,
        mime_type,
    )
    config = types.GenerateContentConfig(
        system_instruction=ONBOARDING_PROMPT,
        temperature=0.1,
        response_mime_type="application/json",
    )

    try:
        client = _get_client()
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=settings.gemma_model,
                contents=contents,
                config=config,
            ),
        )
        text = response.text or ""
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemma error: {exc}") from exc

    try:
        return _extract_json(text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model returned invalid JSON: {exc}") from exc
