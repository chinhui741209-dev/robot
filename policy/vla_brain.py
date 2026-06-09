#!/usr/bin/env python3
"""
Claude VLA "brain": natural-language command + camera image -> structured task plan.

Replaces the GPU-only OpenVLA path with a Claude vision+language call that emits
the SAME parsed-command shape task_parser produces:
    {intent, source, target, steps: [...]}
so the Phase 2 event-driven planner consumes it unchanged ("VLA as brain, BC as
small-brain": the plan drives the closed-loop planner -> policy/skill execution).

Auth: env only (never committed). `anthropic.Anthropic()` resolves ANTHROPIC_API_KEY,
then ANTHROPIC_AUTH_TOKEN (OAuth bearer), then an `ant auth login` profile. For
OAuth set ANTHROPIC_AUTH_TOKEN and leave ANTHROPIC_API_KEY unset (both set -> 401).
API/SDK import is lazy; the pure parser `parse_plan` is unit-testable without the SDK.
"""

EMIT_TOOL = {
    "name": "emit_task_plan",
    "description": "Emit a structured manipulation task plan for the robot.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "description": "e.g. pick_and_place"},
            "source": {"type": "string", "description": "object to act on (lowercase), or empty"},
            "target": {"type": "string", "description": "destination object (lowercase), or empty"},
            "steps": {"type": "array", "items": {"type": "string"},
                      "description": "ordered step names, e.g. locate_pen, grasp_pen, move_to_box, release_pen"},
        },
        "required": ["intent", "source", "target", "steps"],
        "additionalProperties": False,
    },
}

DEFAULT_MODEL = "claude-opus-4-8"


def parse_plan(tool_input):
    """Pure: validate/normalize an emit_task_plan tool input into a parsed_command dict."""
    if not isinstance(tool_input, dict):
        return None
    steps = tool_input.get("steps") or []
    steps = [str(s).strip() for s in steps if str(s).strip()]
    if not steps:
        return None
    return {
        "intent": str(tool_input.get("intent", "")).strip() or "task",
        "source": str(tool_input.get("source", "")).strip().lower(),
        "target": str(tool_input.get("target", "")).strip().lower(),
        "steps": steps,
    }


class ClaudeVlaBrain:
    def __init__(self, model=DEFAULT_MODEL, max_tokens=1024, logger=None):
        self.model = model
        self.max_tokens = max_tokens
        self._log = logger
        import anthropic
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()

    def _warn(self, msg):
        if self._log:
            self._log.warn(msg)

    def plan(self, command, frame_bgr=None, scene_objects=None):
        """command: NL string. frame_bgr: optional image. scene_objects: optional
        list of {class,...} the world model already sees. Returns parsed_command dict or None."""
        import cv2
        content = []
        if frame_bgr is not None:
            ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                import base64
                content.append({"type": "image", "source": {
                    "type": "base64", "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(buf.tobytes()).decode("utf-8")}})
        seen = ""
        if scene_objects:
            seen = "Objects currently detected: " + ", ".join(
                sorted({o.get("class", "") for o in scene_objects if o.get("class")})) + ". "
        content.append({"type": "text", "text": (
            f"You are a robot manipulation planner. User command: \"{command}\". {seen}"
            "Produce a task plan via emit_task_plan. Use lowercase object names; step "
            "names like locate_<obj>, grasp_<obj>, move_to_<target>, release_<obj>.")})
        try:
            resp = self.client.messages.create(
                model=self.model, max_tokens=self.max_tokens,
                tools=[EMIT_TOOL], tool_choice={"type": "tool", "name": "emit_task_plan"},
                messages=[{"role": "user", "content": content}],
            )
        except Exception as e:
            self._warn(f"Claude VLA call failed: {e}")
            return None
        tool_input = next((b.input for b in resp.content
                           if getattr(b, "type", None) == "tool_use"), None)
        return parse_plan(tool_input) if tool_input is not None else None
