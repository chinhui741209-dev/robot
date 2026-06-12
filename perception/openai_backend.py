#!/usr/bin/env python3
"""
OpenAI Vision detection backend (open-vocabulary) — pure stdlib HTTP.

A non-Anthropic alternative used ONLY by the interactive Demo Studio object
lock, for when the available credential is an OpenAI key. It is deliberately
kept separate from the Claude path (perception/api_backend.py) — the two are
never mixed. Given a camera frame + target hint(s), it asks an OpenAI
vision-capable model (Chat Completions, JSON mode) to return detections in the
SAME normalized shape the Claude tool uses, then reuses the pure
`parse_detections` parser so the output is identical:
{class, score, cx, cy, w, h, depth} in frame pixels.

Implementation: stdlib `urllib` only (no `openai` SDK, no `requests`) so it runs
on the Orin without any pip install. Credentials from the environment only:
OPENAI_API_KEY (required), OPENAI_MODEL (default gpt-4o), OPENAI_BASE_URL
(default https://api.openai.com/v1). No/invalid key or any error -> returns []
(the studio then falls back to click-to-lock).
"""

import json
import os
import urllib.request

from perception.api_backend import parse_detections

DEFAULT_MODEL = "gpt-4o"
DEFAULT_BASE = "https://api.openai.com/v1"

_PROMPT = (
    "You are an open-vocabulary object detector. Detect the physical objects in "
    "the image, paying special attention to: {hints}. Respond ONLY with a JSON "
    "object of this exact shape:\n"
    '{{"detections": [{{"label": "<lowercase name>", "confidence": <0..1>, '
    '"cx": <0..1>, "cy": <0..1>, "w": <0..1>, "h": <0..1>, "depth_m": <metres>}}]}}\n'
    "cx,cy,w,h are the bounding-box centre and size NORMALIZED to the image "
    "(0..1). depth_m is your estimate of the distance from the camera in metres. "
    "Return an empty list if nothing relevant is visible."
)


def build_payload(b64_jpeg, hints, model=DEFAULT_MODEL):
    """Pure: assemble the Chat Completions request body (JSON mode, vision)."""
    hint_str = ", ".join(hints) if hints else "any nameable object"
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": _PROMPT.format(hints=hint_str)},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_jpeg}", "detail": "low"}},
            ]},
        ],
    }


def parse_response(raw_text, frame_w, frame_h, conf_thresh=0.3):
    """Pure: OpenAI response JSON text -> pixel detection dicts.

    Accepts the full Chat Completions response (str/bytes/dict); pulls
    choices[0].message.content, json-loads it, and reuses parse_detections.
    Returns [] on any malformed input.
    """
    try:
        resp = raw_text if isinstance(raw_text, dict) else json.loads(raw_text)
        content = resp["choices"][0]["message"]["content"]
        tool_input = content if isinstance(content, dict) else json.loads(content)
    except (KeyError, IndexError, TypeError, ValueError):
        return []
    return parse_detections(tool_input, frame_w, frame_h, conf_thresh=conf_thresh)


class OpenAIVisionDetector:
    """Open-vocab detector over OpenAI vision via stdlib HTTP. detect()->[] on error."""

    def __init__(self, model=None, conf_thresh=0.3, timeout=20, logger=None):
        self.model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
        self.base = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE).rstrip("/")
        self.conf_thresh = conf_thresh
        self.timeout = timeout
        self._log = logger

    def _warn(self, msg):
        if self._log:
            self._log.warn(msg)

    def detect(self, frame_bgr, class_hints=None):
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            self._warn("OPENAI_API_KEY not set")
            return []
        try:
            import cv2
            ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                return []
            import base64
            b64 = base64.standard_b64encode(buf.tobytes()).decode("ascii")
        except Exception as e:
            self._warn(f"encode failed: {e}")
            return []

        h, w = frame_bgr.shape[:2]
        body = json.dumps(build_payload(b64, class_hints, self.model)).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/chat/completions", data=body, method="POST",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode("utf-8")
        except Exception as e:
            self._warn(f"OpenAI vision call failed: {e}")
            return []
        return parse_response(raw, w, h, conf_thresh=self.conf_thresh)
