#!/usr/bin/env python3
"""
Claude Vision API detection backend (open-vocabulary; no local training).

A pluggable alternative to the local YOLOv8 detector: given a camera frame and
class hints, Claude vision returns detections via a strict tool call. Output is
the SAME dict shape as perception/detection_utils.decode_yolov8
({class, score, cx, cy, w, h} in frame pixels) so all downstream consumers
(perception_node -> /perception/objects -> world_model/planner/GUI) are unchanged.

Auth: credentials are resolved from the environment by the SDK only — never
hardcoded, never committed. `anthropic.Anthropic()` resolves, in order,
ANTHROPIC_API_KEY, then ANTHROPIC_AUTH_TOKEN (OAuth bearer token), then an
`ant auth login` profile. To use OAuth, set ANTHROPIC_AUTH_TOKEN and leave
ANTHROPIC_API_KEY UNSET (if both are set the API rejects the request). OAuth
tokens are short-lived and not auto-refreshed via env var — refresh before
expiry for long-running nodes. No/invalid creds or API error -> returns []
(caller falls back to the local detector). The `anthropic` SDK is imported
lazily so this module (and its pure parser) import fine without the SDK.

Cost/latency: a vision call is ~1-3s and bills the image as input tokens — drive
this at a LOW rate (perception_node `detect_rate`), never the 15 Hz loop.
"""

import base64

# Strict tool schema — Claude must return detections in this exact shape.
REPORT_TOOL = {
    "name": "report_detections",
    "description": "Report every distinct physical object visible in the image.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "detections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "description": "object class name, lowercase"},
                        "confidence": {"type": "number", "description": "0..1"},
                        "cx": {"type": "number", "description": "bbox center x, normalized 0..1"},
                        "cy": {"type": "number", "description": "bbox center y, normalized 0..1"},
                        "w": {"type": "number", "description": "bbox width, normalized 0..1"},
                        "h": {"type": "number", "description": "bbox height, normalized 0..1"},
                        "depth_m": {"type": "number",
                                    "description": "estimated distance from camera to object, in metres"},
                    },
                    "required": ["label", "confidence", "cx", "cy", "w", "h", "depth_m"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["detections"],
        "additionalProperties": False,
    },
}

DEFAULT_MODEL = "claude-opus-4-8"  # per claude-api guidance; switch to sonnet/haiku to cut cost


def parse_detections(tool_input, frame_w, frame_h, conf_thresh=0.3):
    """Pure: convert a report_detections tool input (normalized) to pixel dicts.

    tool_input: {"detections": [{label, confidence, cx, cy, w, h}, ...]} with
    cx/cy/w/h normalized 0..1. Returns list of {class, score, cx, cy, w, h} in
    frame pixels — same shape as decode_yolov8. ROS/SDK-free and unit-testable.
    """
    out = []
    if not isinstance(tool_input, dict):
        return out
    for d in tool_input.get("detections", []) or []:
        try:
            score = float(d["confidence"])
            if score < conf_thresh:
                continue
            cx = max(0.0, min(1.0, float(d["cx"]))) * frame_w
            cy = max(0.0, min(1.0, float(d["cy"]))) * frame_h
            w = max(0.0, min(1.0, float(d["w"]))) * frame_w
            h = max(0.0, min(1.0, float(d["h"]))) * frame_h
            label = str(d["label"]).strip().lower()
            if not label:
                continue
            depth = None
            if d.get("depth_m") is not None:
                try:
                    depth = float(d["depth_m"])
                    if depth <= 0:
                        depth = None
                except (TypeError, ValueError):
                    depth = None
            out.append({"class": label, "score": score,
                        "cx": cx, "cy": cy, "w": w, "h": h, "depth": depth})
        except (KeyError, TypeError, ValueError):
            continue
    return out


class ClaudeVisionDetector:
    """Open-vocabulary detector backed by the Claude vision API."""

    def __init__(self, model=DEFAULT_MODEL, conf_thresh=0.3, max_tokens=2048, logger=None):
        self.model = model
        self.conf_thresh = conf_thresh
        self.max_tokens = max_tokens
        self._log = logger
        import anthropic  # lazy — only needed when the API backend is actually used
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()  # env: ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN (OAuth)

    def _warn(self, msg):
        if self._log:
            self._log.warn(msg)

    def detect(self, frame_bgr, class_hints=None):
        """frame_bgr: HxWx3 BGR ndarray. Returns list of detection dicts (pixels)."""
        import cv2
        h, w = frame_bgr.shape[:2]
        ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return []
        b64 = base64.standard_b64encode(buf.tobytes()).decode("utf-8")
        hint = (f"Pay special attention to these classes: {', '.join(class_hints)}. "
                if class_hints else "")
        prompt = (f"Detect the physical objects in this robot camera image. {hint}"
                  "Report any clearly visible object. Coordinates normalized 0..1, "
                  "origin top-left. Use lowercase singular labels. Also estimate "
                  "depth_m = the distance in metres from the camera to each object.")
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                tools=[REPORT_TOOL],
                tool_choice={"type": "tool", "name": "report_detections"},
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {
                            "type": "base64", "media_type": "image/jpeg", "data": b64}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
        except self._anthropic.APIError as e:
            self._warn(f"Claude vision API error: {e}")
            return []
        except Exception as e:  # network / unexpected
            self._warn(f"Claude vision call failed: {e}")
            return []

        tool_input = next((b.input for b in resp.content
                           if getattr(b, "type", None) == "tool_use"), None)
        if tool_input is None:
            return []
        return parse_detections(tool_input, w, h, conf_thresh=self.conf_thresh)
