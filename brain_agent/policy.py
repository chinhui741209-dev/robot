#!/usr/bin/env python3
"""
大腦 Agent 的後端選擇政策（純）。

mode      : "cloud" | "local" | "auto"（預設 auto）— 偏好雲端 / 只用本地 / 自動依 order。
on_prem   : True 時**硬性禁用所有 is_cloud 後端**（保證不上雲，給資料敏感客戶）。
order     : 各 capability 的偏好後端名順序（auto 模式用；cloud/local 模式仍依此序但先過濾）。
"""

import os
from dataclasses import dataclass, field


DEFAULT_ORDER = {
    "vision":   ["gemini", "claude-vision", "openai", "qwen-local", "onnx"],
    "planning": ["claude", "gemini", "rule"],
    "action":   ["gr00t"],
}


@dataclass
class Policy:
    mode: str = "auto"                  # cloud | local | auto
    on_prem: bool = False
    order: dict = field(default_factory=lambda: {k: list(v) for k, v in DEFAULT_ORDER.items()})

    @staticmethod
    def from_env(env=None):
        env = env if env is not None else os.environ
        mode = (env.get("BRAIN_MODE") or "auto").strip().lower()
        if mode not in ("cloud", "local", "auto"):
            mode = "auto"
        on_prem = str(env.get("BRAIN_ON_PREM", "")).strip().lower() in ("1", "true", "yes")
        return Policy(mode=mode, on_prem=on_prem)

    def allows_cloud(self) -> bool:
        """on_prem 一律禁雲；local 模式也不用雲端。"""
        return (not self.on_prem) and (self.mode != "local")
