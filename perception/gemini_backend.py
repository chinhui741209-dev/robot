#!/usr/bin/env python3
"""
Gemini (Google) Vision detection backend (open-vocabulary) — pure stdlib HTTP.

A non-Anthropic alternative used ONLY by the interactive Demo Studio object
lock, kept separate from the Claude path (never mixed). Given a camera frame +
target hint(s), it asks a Gemini vision model (generateContent, JSON response)
to return detections in the SAME normalized shape the Claude tool uses, then
reuses the pure `parse_detections` parser so the output is identical:
{class, score, cx, cy, w, h, depth} in frame pixels.

Implementation: stdlib `urllib` only (no google SDK, no requests) so it runs on
the Orin without any pip install. Credentials from the environment only:
GEMINI_API_KEY (required), GEMINI_MODEL (default gemini-2.5-flash),
GEMINI_BASE_URL (default the v1beta generativelanguage endpoint). No/invalid key
or any error -> returns [] (the studio then tries the next backend / fallback).
"""

import json
import os
import urllib.request

from perception.api_backend import parse_detections

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta"

_PROMPT = (
    "You are an open-vocabulary object detector. Detect the physical objects in "
    "the image, paying special attention to: {hints}. Respond ONLY with JSON of "
    "this exact shape:\n"
    '{{"detections": [{{"label": "<lowercase name>", "confidence": <0..1>, '
    '"cx": <0..1>, "cy": <0..1>, "w": <0..1>, "h": <0..1>, "depth_m": <metres>}}]}}\n'
    "cx,cy,w,h are the bounding-box centre and size NORMALIZED to the image "
    "(0..1). depth_m is the estimated distance from the camera in metres. Return "
    "an empty list if nothing relevant is visible."
)


def build_payload(b64_jpeg, hints):
    """Pure: assemble the generateContent request body (vision, JSON output)."""
    hint_str = ", ".join(hints) if hints else "any nameable object"
    return {
        "contents": [{"parts": [
            {"text": _PROMPT.format(hints=hint_str)},
            {"inline_data": {"mime_type": "image/jpeg", "data": b64_jpeg}},
        ]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }


def parse_response(raw_text, frame_w, frame_h, conf_thresh=0.3):
    """Pure: Gemini generateContent response -> pixel detection dicts.

    Pulls candidates[0].content.parts[*].text, json-loads it, and reuses
    parse_detections. Returns [] on any malformed input.
    """
    try:
        resp = raw_text if isinstance(raw_text, dict) else json.loads(raw_text)
        parts = resp["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts) if isinstance(parts, list) else ""
        tool_input = json.loads(text)
    except (KeyError, IndexError, TypeError, ValueError):
        return []
    return parse_detections(tool_input, frame_w, frame_h, conf_thresh=conf_thresh)


class GeminiVisionDetector:
    """Open-vocab detector over Gemini vision via stdlib HTTP. detect()->[] on error."""

    def __init__(self, model=None, conf_thresh=0.3, timeout=25, logger=None):
        self.model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        self.base = os.environ.get("GEMINI_BASE_URL", DEFAULT_BASE).rstrip("/")
        self.conf_thresh = conf_thresh
        self.timeout = timeout
        self._log = logger

    def _warn(self, msg):
        if self._log:
            self._log.warn(msg)

    def detect(self, frame_bgr, class_hints=None):
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            self._warn("GEMINI_API_KEY not set")
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
        body = json.dumps(build_payload(b64, class_hints)).encode("utf-8")
        url = f"{self.base}/models/{self.model}:generateContent?key={key}"
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode("utf-8")
        except Exception as e:
            self._warn(f"Gemini vision call failed: {e}")
            return []
        return parse_response(raw, w, h, conf_thresh=self.conf_thresh)
