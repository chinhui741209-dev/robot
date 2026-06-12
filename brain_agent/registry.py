#!/usr/bin/env python3
"""
BackendRegistry：登錄後端，依政策與能力回傳「候選後端」有序清單（純）。

選擇規則（candidates）：
  1. 取支援該 capability 的後端。
  2. 依政策過濾：on_prem 或 local 模式 → 去掉 is_cloud 後端；
     若無法用雲端則同時去掉所有 cloud（保證不上雲）。
  3. 排序：依 policy.order[capability] 的名次；未列名者排在最後（保序）。
  4. 只回傳 available() 為真者。
回傳順序即 BrainAgent 的嘗試（fallback）順序。
"""


class BackendRegistry:
    def __init__(self, backends=None):
        self._backends = list(backends or [])

    def register(self, backend):
        self._backends.append(backend)
        return self

    def all(self):
        return list(self._backends)

    def candidates(self, capability, policy, check_available=True):
        order = policy.order.get(capability, [])

        def rank(b):
            return order.index(b.name) if b.name in order else len(order)

        elig = []
        for b in self._backends:
            if not b.has(capability):
                continue
            if b.is_cloud and not policy.allows_cloud():
                continue  # on_prem / local：禁雲
            if check_available and not _safe_available(b):
                continue
            elig.append(b)
        elig.sort(key=rank)
        return elig


def _safe_available(backend) -> bool:
    """available() 不應拋例外；若拋了，視為不可用。"""
    try:
        return bool(backend.available())
    except Exception:
        return False
