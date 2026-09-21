"""VLM backend for demo-based AI-assisted annotation (doc section 3.1).

Not wired to a real model in this scaffold — ANNOTATION_VLM_ENDPOINT is
empty by default, so `suggest()` returns a clear "not configured" error
per image instead of pretending to produce a suggestion. Point it at an
OpenAI-vision-compatible chat/completions endpoint (a local vLLM/Ollama
server running ANNOTATION_VLM_MODEL, or a cloud VLM) and implement the
request/response mapping in `_call_vlm` to go live — nothing else in the
pipeline (confidence gating, risk scoring, review queue) needs to change.
"""

import base64

import httpx

from .config import settings


class VLMNotConfigured(Exception):
    pass


def _call_vlm(image_bytes: bytes, demos: list[dict], text_description: str) -> dict:
    if not settings.annotation_vlm_endpoint:
        raise VLMNotConfigured("ANNOTATION_VLM_ENDPOINT is not set")

    # Example shape for an OpenAI-vision-compatible endpoint — adjust to
    # match whatever server ANNOTATION_VLM_ENDPOINT actually points at.
    image_b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "model": settings.annotation_vlm_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_description or "Detect the described defect and return its bounding box."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }
        ],
    }
    resp = httpx.post(settings.annotation_vlm_endpoint, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def suggest(image_bytes: bytes, demos: list[dict], text_description: str) -> dict:
    """Returns {"bbox_x","bbox_y","bbox_w","bbox_h","confidence"} in pixel
    coordinates, or raises VLMNotConfigured / httpx errors."""
    _call_vlm(image_bytes, demos, text_description)
    raise NotImplementedError(
        "wire up response parsing for your VLM's output format once ANNOTATION_VLM_ENDPOINT is live"
    )
