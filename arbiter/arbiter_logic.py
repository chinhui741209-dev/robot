#!/usr/bin/env python3
"""Pure arbitration decision (ROS-free, unit-testable)."""


def arbitrate(mode, policy_cmd, skill_cmd):
    """Return (source, command_list) for the given mode.

    source in {"policy", "skill", "idle"}; command may be [] when holding.
      LOCOMOTION   -> policy (32-DoF) wins
      MANIPULATION -> skill (4-DoF arm) wins
      IDLE/other   -> hold (no output)
    """
    if mode == "MANIPULATION" and skill_cmd:
        return "skill", list(skill_cmd)
    if mode == "LOCOMOTION" and policy_cmd:
        return "policy", list(policy_cmd)
    return "idle", []
