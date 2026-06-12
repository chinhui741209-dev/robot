"""
大腦 Agent 抽象層（BrainAgent）—— 單一 agent、模型後端可抽換（雲端 LLM ↔ 本地）。

採宇樹廠商定義。規格見 Robot_C docs/architecture/brain-agent.md。

模組：
  base      ModelBackend 介面 + Capability + 決策紀錄（純）
  policy    Policy（mode/on_prem/order）+ from_env（純）
  registry  BackendRegistry：依政策過濾/排序可用後端（純）
  agent     BrainAgent：select / detect / plan + fallback 鏈 + 稽核紀錄
  backends  adapter，包現有 perception/task_parser 後端（重型相依延遲匯入）

核心（base/policy/registry/agent）不依賴 ROS/torch/網路，可在開發機單元測試；
backends 的 adapter 只在實際用到時才 import 對應後端。
"""

from brain_agent.base import Capability, ModelBackend, Decision
from brain_agent.policy import Policy
from brain_agent.registry import BackendRegistry
from brain_agent.agent import BrainAgent

__all__ = ["Capability", "ModelBackend", "Decision", "Policy", "BackendRegistry", "BrainAgent"]
