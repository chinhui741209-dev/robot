#!/usr/bin/env python3
"""
Event-driven step sequencer for the Planner (pure, ROS-free, unit-testable).

Replaces the old open-loop "+1 every second" planner. Each step has a
perceptual precondition derived from the parsed command (which object must be
present, per the world model). A step advances only once its precondition has
held for `confirm_needed` consecutive updates. If it is not satisfied within
`timeout_s`, the step is retried (up to `max_retries`); exhausting retries
moves the task to FAILED.

States: IDLE, RUNNING, COMPLETED, FAILED.
"""

# State constants.
IDLE = "IDLE"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"


def step_precondition(step_name, source, target):
    """Which object class (if any) must be present for this step to advance."""
    s = (step_name or "").lower()
    if "move_to" in s or "release" in s or (target and target in s):
        return target
    if "locate" in s or "grasp" in s or "pick" in s or (source and source in s):
        return source
    return None  # no perceptual gate — dwell-only step


class StepSequencer:
    def __init__(self, steps, source=None, target=None,
                 confirm_needed=2, timeout_s=5.0, max_retries=2):
        self.steps = list(steps) if steps else []
        self.source = source
        self.target = target
        self.confirm_needed = int(confirm_needed)
        self.timeout_s = float(timeout_s)
        self.max_retries = int(max_retries)

        self.idx = 0 if self.steps else -1
        self.state = RUNNING if self.steps else IDLE
        self._confirm = 0
        self._retries = 0
        self._step_start = None
        self.last_reason = ""

    def current_step(self):
        if 0 <= self.idx < len(self.steps):
            return self.steps[self.idx]
        return None

    def precondition(self):
        return step_precondition(self.current_step(), self.source, self.target)

    def update(self, present_classes, now):
        """Advance the state machine. Returns an event dict.

        present_classes: iterable of class names the world model reports present.
        now: monotonic seconds.
        """
        if self.state in (COMPLETED, FAILED, IDLE):
            return self._event(advanced=False)

        if self._step_start is None:
            self._step_start = now

        req = self.precondition()
        satisfied = (req is None) or (req in set(present_classes))

        advanced = False
        if satisfied:
            self._confirm += 1
            if self._confirm >= self.confirm_needed:
                advanced = self._advance(now)
        else:
            self._confirm = 0
            if (now - self._step_start) > self.timeout_s:
                self._retries += 1
                if self._retries > self.max_retries:
                    self.state = FAILED
                    self.last_reason = f"timeout waiting for '{req}' (step {self.idx})"
                else:
                    self.last_reason = f"retry {self._retries} waiting for '{req}'"
                    self._step_start = now  # restart this step's clock

        return self._event(advanced=advanced)

    def _advance(self, now):
        self.idx += 1
        self._confirm = 0
        self._retries = 0
        self._step_start = now
        if self.idx >= len(self.steps):
            self.state = COMPLETED
            self.idx = len(self.steps) - 1  # clamp for reporting
            self.last_reason = "all steps completed"
        else:
            self.last_reason = f"advanced to '{self.current_step()}'"
        return True

    def _event(self, advanced):
        return {
            "idx": self.idx,
            "step": self.current_step(),
            "state": self.state,
            "precondition": self.precondition() if self.state == RUNNING else None,
            "confirm": self._confirm,
            "retries": self._retries,
            "reason": self.last_reason,
            "advanced": advanced,
        }
