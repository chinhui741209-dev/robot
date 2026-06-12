#!/usr/bin/env python3
"""
BrainAgent 核心（policy/registry/agent）單元測試 —— 純，用假後端，無 ROS/torch/網路/金鑰。
執行：PYTHONPATH=. pytest tests/test_brain_agent.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_agent.base import Capability, ModelBackend
from brain_agent.policy import Policy
from brain_agent.registry import BackendRegistry
from brain_agent.agent import BrainAgent


class FakeVision(ModelBackend):
    def __init__(self, name, is_cloud, result=None, exc=False, avail=True):
        self.name, self.is_cloud = name, is_cloud
        self.capabilities = frozenset({Capability.VISION})
        self._result, self._exc, self._avail = (result or []), exc, avail
        self.calls = 0

    def available(self):
        return self._avail

    def detect(self, frame_bgr, class_hints=None):
        self.calls += 1
        if self._exc:
            raise RuntimeError("boom")
        return self._result


class FakePlan(ModelBackend):
    def __init__(self, name, is_cloud, result=None, avail=True):
        self.name, self.is_cloud = name, is_cloud
        self.capabilities = frozenset({Capability.PLANNING})
        self._result, self._avail = result, avail

    def available(self):
        return self._avail

    def plan(self, command, scene=None, frame_bgr=None):
        return self._result


def _order(vision, planning):
    return {"vision": vision, "planning": planning, "action": []}


# ---- policy / registry 過濾 ------------------------------------------------

def test_on_prem_filters_cloud():
    reg = BackendRegistry([FakeVision("gemini", True), FakeVision("onnx", False)])
    pol = Policy(mode="auto", on_prem=True, order=_order(["gemini", "onnx"], []))
    names = [b.name for b in reg.candidates(Capability.VISION, pol)]
    assert names == ["onnx"]              # 雲端被硬性濾掉


def test_local_mode_filters_cloud():
    reg = BackendRegistry([FakeVision("gemini", True), FakeVision("qwen-local", False)])
    pol = Policy(mode="local", order=_order(["gemini", "qwen-local"], []))
    assert [b.name for b in reg.candidates(Capability.VISION, pol)] == ["qwen-local"]


def test_auto_orders_by_policy_and_cloud_allowed():
    reg = BackendRegistry([FakeVision("onnx", False), FakeVision("gemini", True)])
    pol = Policy(mode="auto", order=_order(["gemini", "onnx"], []))
    assert [b.name for b in reg.candidates(Capability.VISION, pol)] == ["gemini", "onnx"]


def test_unavailable_excluded():
    reg = BackendRegistry([FakeVision("gemini", True, avail=False), FakeVision("onnx", False)])
    pol = Policy(mode="auto", order=_order(["gemini", "onnx"], []))
    assert [b.name for b in reg.candidates(Capability.VISION, pol)] == ["onnx"]


# ---- fallback ---------------------------------------------------------------

def test_detect_falls_back_on_exception():
    g = FakeVision("gemini", True, exc=True)
    o = FakeVision("onnx", False, result=[{"class": "pen", "score": 0.9}])
    agent = BrainAgent(BackendRegistry([g, o]), Policy(mode="auto", order=_order(["gemini", "onnx"], [])))
    out = agent.detect(frame_bgr=None)
    assert out and out[0]["class"] == "pen"
    d = agent.last_decision
    assert d.backend == "onnx" and d.fell_back is True and d.ok is True
    assert d.tried == ["gemini", "onnx"] and d.is_cloud is False


def test_detect_falls_back_on_empty():
    g = FakeVision("gemini", True, result=[])              # 雲端回空
    o = FakeVision("onnx", False, result=[{"class": "box", "score": 0.8}])
    agent = BrainAgent(BackendRegistry([g, o]), Policy(mode="auto", order=_order(["gemini", "onnx"], [])))
    out = agent.detect(frame_bgr=None)
    assert out and out[0]["class"] == "box"
    assert agent.last_decision.backend == "onnx"


def test_plan_uses_first_available_and_records_cloud():
    c = FakePlan("claude", True, result={"intent": "pick", "source": "pen", "target": "", "steps": []})
    r = FakePlan("rule", False, result={"intent": "rule", "source": "x", "target": "", "steps": []})
    agent = BrainAgent(BackendRegistry([c, r]), Policy(mode="auto", order=_order([], ["claude", "rule"])))
    plan = agent.plan("pick up the pen")
    assert plan["intent"] == "pick"
    assert agent.last_decision.backend == "claude" and agent.last_decision.is_cloud is True


def test_plan_on_prem_skips_cloud_uses_rule():
    c = FakePlan("claude", True, result={"intent": "pick"})
    r = FakePlan("rule", False, result={"intent": "rule"})
    agent = BrainAgent(BackendRegistry([c, r]),
                       Policy(mode="auto", on_prem=True, order=_order([], ["claude", "rule"])))
    plan = agent.plan("把筆撿起來")
    assert plan["intent"] == "rule"
    assert agent.last_decision.is_cloud is False and agent.last_decision.backend == "rule"


def test_no_candidate_returns_empty():
    agent = BrainAgent(BackendRegistry([FakeVision("gemini", True)]),
                       Policy(mode="local", order=_order(["gemini"], [])))  # local 濾掉唯一雲端
    assert agent.detect(frame_bgr=None) == []
    assert agent.last_decision.backend == "(none)" and agent.last_decision.ok is False


# ---- policy.from_env --------------------------------------------------------

def test_policy_from_env():
    assert Policy.from_env({}).mode == "auto"
    assert Policy.from_env({"BRAIN_MODE": "local"}).mode == "local"
    assert Policy.from_env({"BRAIN_MODE": "bogus"}).mode == "auto"
    assert Policy.from_env({"BRAIN_ON_PREM": "1"}).on_prem is True
    assert Policy.from_env({"BRAIN_ON_PREM": "0"}).on_prem is False
    # on_prem 時 allows_cloud 為 False；local 模式亦然
    assert Policy(mode="cloud", on_prem=True).allows_cloud() is False
    assert Policy(mode="local").allows_cloud() is False
    assert Policy(mode="cloud").allows_cloud() is True
