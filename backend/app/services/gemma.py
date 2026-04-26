import base64
import json
import re
from typing import Any

import httpx
from fastapi import HTTPException

from ..config import ONBOARDING_PROMPT, settings


def _extract_json(payload: str) -> dict[str, Any]:
    payload = payload.strip()
    if payload.startswith("{"):
        return json.loads(payload)
    match = re.search(r"\{.*\}", payload, flags=re.S)
    if not match:
        raise ValueError("No JSON object found in model response.")
    return json.loads(match.group(0))


def _gemini_endpoint() -> str:
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemma_model}:generateContent?key={settings.effective_api_key}"
    )


async def call_gemma_text(
    system: str,
    user_text: str,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
) -> str:
    """Call Gemma 4 with optional image. Returns plain text response."""
    if not settings.effective_api_key:
        return "AI service not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY in backend/.env."

    parts: list[dict[str, Any]] = [{"text": user_text}]
    if image_bytes:
        parts.append({
            "inlineData": {
                "mimeType": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
        })

    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.4},
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(_gemini_endpoint(), json=payload)
        resp.raise_for_status()
        data = resp.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (IndexError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Invalid model response: {exc}") from exc


async def call_gemma_with_qr(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    """Call Gemma 4 with a QR/onboarding image; returns parsed JSON dict."""
    if not settings.effective_api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY or GOOGLE_API_KEY is missing in backend/.env.",
        )

    payload = {
        "systemInstruction": {"parts": [{"text": ONBOARDING_PROMPT}]},
        "contents": [
            {
                "parts": [
                    {"text": "Parse this medical onboarding QR image and classify active agents."},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(_gemini_endpoint(), json=payload)
        response.raise_for_status()
        data = response.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (IndexError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Invalid model response shape: {exc}") from exc

    try:
        return _extract_json(text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model returned invalid JSON: {exc}") from exc
