#!/usr/bin/env python3
"""
Pluggable language backends for the task parser (NL command -> task plan).

RuleBackend (default, offline, deterministic): a verb + object lexicon does slot
extraction, generalizing beyond the old 3 hardcoded commands to any source/target
combination (zh + en). Pure — unit-testable without ROS or network.

LLMBackend (opt-in via ANTHROPIC_API_KEY): Claude (text-only) emits a structured
plan, reusing policy/vla_brain's EMIT_TOOL + parse_plan so the schema never drifts.

Both return the parsed_command dict the Phase 2 planner consumes:
    {intent, source, target, steps}
"""

# NL word (zh + en) -> canonical class label (aligned with perception/classes.py).
LEXICON = {
    "pen": "pen", "筆": "pen",
    "box": "box", "盒子": "box", "箱子": "box", "箱": "box",
    "apple": "apple", "蘋果": "apple",
    "orange": "orange", "橘子": "orange", "柳橙": "orange",
    "cup": "cup", "杯子": "cup", "杯": "cup",
    "bottle": "bottle", "瓶子": "bottle", "瓶": "bottle",
}
PLACE_VERBS = ("放", "put", "place", "into", "到", "進", "入")


def steps_for(intent, source, target):
    if intent == "pick_and_place":
        return [f"locate_{source}", f"grasp_{source}", f"move_to_{target}", f"release_{source}"]
    return [f"locate_{source}", f"grasp_{source}"]


def parse_rule(command):
    """NL command -> {intent, source, target, steps} | None (pure, offline)."""
    if not command:
        return None
    c = command.strip().lower()  # lowercases ASCII; CJK unaffected
    # Collect canonical objects by first position in the command.
    pos = {}
    for word, canon in LEXICON.items():
        i = c.find(word.lower())
        if i >= 0 and (canon not in pos or i < pos[canon]):
            pos[canon] = i
    objs = [canon for canon, _ in sorted(pos.items(), key=lambda kv: kv[1])]
    if not objs:
        return None

    has_place = any(v in c for v in PLACE_VERBS)
    if len(objs) >= 2 and has_place:
        intent, source, target = "pick_and_place", objs[0], objs[1]
    else:
        intent, source, target = "pick", objs[0], ""
    return {"intent": intent, "source": source, "target": target,
            "steps": steps_for(intent, source, target)}


class RuleBackend:
    name = "rule"

    def parse(self, command):
        return parse_rule(command)


class LLMBackend:
    name = "llm"

    def __init__(self, model="claude-opus-4-8", logger=None):
        self.model = model
        self._log = logger
        import anthropic
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()  # env: ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN

    def parse(self, command):
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from policy.vla_brain import EMIT_TOOL, parse_plan
        try:
            resp = self.client.messages.create(
                model=self.model, max_tokens=1024,
                tools=[EMIT_TOOL], tool_choice={"type": "tool", "name": "emit_task_plan"},
                messages=[{"role": "user", "content": (
                    f"Parse this robot command into a task plan: \"{command}\". "
                    "Use lowercase object names; steps like locate_<obj>, grasp_<obj>, "
                    "move_to_<target>, release_<obj>.")}],
            )
        except Exception as e:
            if self._log:
                self._log.warn(f"LLM parse failed ({e}); use rule fallback")
            return None
        ti = next((b.input for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
        return parse_plan(ti) if ti is not None else None
