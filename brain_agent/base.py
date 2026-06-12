#!/usr/bin/env python3
"""
大腦 Agent 抽象層的核心型別（純，無 ROS/torch/網路）。

ModelBackend：所有模型後端（雲端或本地）實作的共同介面。
Capability：後端能做的事（vision / planning / action）。
Decision：一次後端選擇/執行的稽核紀錄（含是否上雲、是否 fallback）。
"""

from dataclasses import dataclass, field


# ---- 能力常數 --------------------------------------------------------------
class Capability:
    VISION = "vision"        # 影像(+類別提示) → 偵測/分類 dict list
    PLANNING = "planning"    # 自然語言指令(+場景) → 任務計畫 dict
    ACTION = "action"        # 觀測(+指令) → 動作（VLA，未來）
    ALL = (VISION, PLANNING, ACTION)


class ModelBackend:
    """模型後端介面。adapter 子類別實作對應能力的方法。

    屬性：
      name: 唯一名稱（例 "gemini", "qwen-local", "rule"）。
      capabilities: 此後端支援的能力集合（Capability 子集）。
      is_cloud: True=資料會送往外部（雲端）；False=本地不上雲。
    方法（依 capabilities 實作其一/多）：
      available() -> bool：金鑰/權重/裝置是否就緒（不應拋例外）。
      detect(frame_bgr, class_hints=None) -> list[dict]
      plan(command, scene=None, frame_bgr=None) -> dict | None
      act(obs) -> ...（未來）
    """

    name = "base"
    capabilities = frozenset()
    is_cloud = False

    def available(self) -> bool:
        return True

    def detect(self, frame_bgr, class_hints=None):
        raise NotImplementedError

    def plan(self, command, scene=None, frame_bgr=None):
        raise NotImplementedError

    def has(self, capability) -> bool:
        return capability in self.capabilities


@dataclass
class Decision:
    """一次 capability 推論的稽核紀錄。"""
    capability: str
    backend: str                 # 最終成功（或最後嘗試）的後端名
    is_cloud: bool               # 該後端是否上雲（不上雲模式應恆 False）
    tried: list = field(default_factory=list)   # 依序嘗試過的後端名
    fell_back: bool = False      # 是否非第一順位（發生 fallback）
    ok: bool = False             # 是否取得有效結果

    def as_dict(self):
        return {
            "capability": self.capability, "backend": self.backend,
            "is_cloud": self.is_cloud, "tried": list(self.tried),
            "fell_back": self.fell_back, "ok": self.ok,
        }
