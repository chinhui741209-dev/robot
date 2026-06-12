#!/usr/bin/env python3
"""
BrainAgent：依政策挑後端、執行、失敗則沿 fallback 鏈往下試，並記稽核。

detect()/plan() 共用 _run_with_fallback：
  - 依 registry.candidates 順序逐一嘗試；
  - 後端拋例外或回傳「空」結果 → 試下一個；
  - 全失敗 → 回傳空結果（detect: []；plan: None）。
每次呼叫產生一筆 Decision（最後一次成功或最後嘗試的後端 + 是否 fallback + 是否上雲）。
"""

from brain_agent.base import Capability, Decision


def _is_empty(capability, result):
    if result is None:
        return True
    if capability == Capability.VISION:
        return len(result) == 0
    return False  # planning: 非 None 即視為有效


class BrainAgent:
    def __init__(self, registry, policy, logger=None):
        self.registry = registry
        self.policy = policy
        self._log = logger
        self.last_decision = None

    def _warn(self, msg):
        if self._log:
            try:
                self._log.warn(msg)
            except Exception:
                pass

    def select(self, capability):
        """回傳此能力的首選後端（available 且符合政策）；無則 None。"""
        cands = self.registry.candidates(capability, self.policy)
        return cands[0] if cands else None

    def _run_with_fallback(self, capability, call, empty):
        cands = self.registry.candidates(capability, self.policy)
        dec = Decision(capability=capability, backend="(none)", is_cloud=False)
        result = empty
        for i, b in enumerate(cands):
            dec.tried.append(b.name)
            try:
                r = call(b)
            except Exception as e:  # noqa: BLE001
                self._warn(f"[brain] {capability} backend '{b.name}' failed: {e}")
                continue
            if _is_empty(capability, r):
                # 空結果也算這個後端「沒交付」，繼續 fallback（但記住已試）。
                if i < len(cands) - 1:
                    continue
                dec.backend, dec.is_cloud = b.name, b.is_cloud
                dec.fell_back = i > 0
                result = r if r is not None else empty
                break
            dec.backend, dec.is_cloud, dec.fell_back, dec.ok = b.name, b.is_cloud, i > 0, True
            result = r
            break
        self.last_decision = dec
        if not cands:
            self._warn(f"[brain] no available backend for {capability} "
                       f"(mode={self.policy.mode}, on_prem={self.policy.on_prem})")
        return result

    def detect(self, frame_bgr, class_hints=None):
        return self._run_with_fallback(
            Capability.VISION,
            lambda b: b.detect(frame_bgr, class_hints=class_hints),
            empty=[],
        )

    def plan(self, command, scene=None, frame_bgr=None):
        return self._run_with_fallback(
            Capability.PLANNING,
            lambda b: b.plan(command, scene=scene, frame_bgr=frame_bgr),
            empty=None,
        )
