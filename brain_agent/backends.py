#!/usr/bin/env python3
"""
Adapter：把既有 perception / task_parser 後端包成 ModelBackend（不重寫）。

所有重型相依（anthropic / google / torch / cv2 / onnxruntime）都在 available()/detect()/plan()
內**延遲匯入**，因此匯入本模組與核心 brain_agent 不需這些套件（host 可測）。

Vision：gemini / claude-vision / qwen-local / onnx
Planning：claude（LLMBackend）/ rule（RuleBackend）
（openai 視需要再加；planning 的 gemini 後端待 task_parser 支援後補。）
"""

import os

from brain_agent.base import Capability, ModelBackend


def _env_has(*keys):
    return any(os.environ.get(k) for k in keys)


# ---- Vision（雲端）---------------------------------------------------------
class GeminiVisionAdapter(ModelBackend):
    name = "gemini"
    capabilities = frozenset({Capability.VISION})
    is_cloud = True

    def __init__(self, conf_thresh=0.3, logger=None):
        self.conf_thresh, self._log, self._det = conf_thresh, logger, None

    def available(self):
        return _env_has("GEMINI_API_KEY")

    def detect(self, frame_bgr, class_hints=None):
        if self._det is None:
            from perception.gemini_backend import GeminiVisionDetector
            self._det = GeminiVisionDetector(conf_thresh=self.conf_thresh, logger=self._log)
        return self._det.detect(frame_bgr, class_hints=class_hints)


class ClaudeVisionAdapter(ModelBackend):
    name = "claude-vision"
    capabilities = frozenset({Capability.VISION})
    is_cloud = True

    def __init__(self, model="claude-opus-4-8", conf_thresh=0.3, logger=None):
        self.model, self.conf_thresh, self._log, self._det = model, conf_thresh, logger, None

    def available(self):
        return _env_has("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

    def detect(self, frame_bgr, class_hints=None):
        if self._det is None:
            from perception.api_backend import ClaudeVisionDetector
            self._det = ClaudeVisionDetector(model=self.model, conf_thresh=self.conf_thresh,
                                             logger=self._log)
        return self._det.detect(frame_bgr, class_hints=class_hints)


# ---- Vision（本地，不上雲）-------------------------------------------------
class QwenLocalAdapter(ModelBackend):
    name = "qwen-local"
    capabilities = frozenset({Capability.VISION})
    is_cloud = False

    def __init__(self, model=None, conf_thresh=0.3, logger=None):
        self.model, self.conf_thresh, self._log, self._det = model, conf_thresh, logger, None

    def available(self):
        # 需 transformers + CUDA torch 就緒（CPU-only torch 不算可用）。
        try:
            import importlib.util as u
            if u.find_spec("transformers") is None or u.find_spec("torch") is None:
                return False
            import torch
            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def detect(self, frame_bgr, class_hints=None):
        if self._det is None:
            from perception.qwen_backend import QwenVLDetector
            self._det = QwenVLDetector(model=self.model, conf_thresh=self.conf_thresh,
                                       logger=self._log)
        return self._det.detect(frame_bgr, class_hints=class_hints)


class OnnxVisionAdapter(ModelBackend):
    name = "onnx"
    capabilities = frozenset({Capability.VISION})
    is_cloud = False

    def __init__(self, model_path="models/active/detection_v2.onnx",
                 conf_thresh=0.5, iou_thresh=0.45, input_size=224, logger=None):
        self.model_path = model_path
        self.conf_thresh, self.iou_thresh, self.input_size = conf_thresh, iou_thresh, input_size
        self._log, self._session, self._names, self._inp = logger, None, None, None

    def available(self):
        try:
            import importlib.util as u
            if u.find_spec("onnxruntime") is None or u.find_spec("cv2") is None:
                return False
            from perception.classes import resolve_path
            return os.path.isfile(resolve_path(self.model_path))
        except Exception:
            return False

    def detect(self, frame_bgr, class_hints=None):
        import numpy as np
        import cv2
        if self._session is None:
            import onnxruntime as ort
            from perception.classes import resolve_path, get_class_names
            self._session = ort.InferenceSession(resolve_path(self.model_path))
            self._inp = self._session.get_inputs()[0].name
            self._names = get_class_names()
        from perception.detection_utils import decode_yolov8
        img = cv2.resize(frame_bgr, (self.input_size, self.input_size)).astype(np.float32) / 255.0
        blob = np.expand_dims(np.transpose(img, (2, 0, 1)), axis=0)
        out = self._session.run(None, {self._inp: blob})[0]
        return decode_yolov8(out, frame_bgr.shape[1], frame_bgr.shape[0],
                             input_size=self.input_size, conf_thresh=self.conf_thresh,
                             iou_thresh=self.iou_thresh, class_names=self._names)


# ---- Planning --------------------------------------------------------------
class RulePlanAdapter(ModelBackend):
    name = "rule"
    capabilities = frozenset({Capability.PLANNING})
    is_cloud = False

    def __init__(self, logger=None):
        self._log, self._be = logger, None

    def available(self):
        return True  # 離線規則，恆可用（最終保底）

    def plan(self, command, scene=None, frame_bgr=None):
        if self._be is None:
            from task_parser.language_backend import RuleBackend
            self._be = RuleBackend()
        return self._be.parse(command)


class ClaudePlanAdapter(ModelBackend):
    name = "claude"
    capabilities = frozenset({Capability.PLANNING})
    is_cloud = True

    def __init__(self, model="claude-opus-4-8", logger=None):
        self.model, self._log, self._be = model, logger, None

    def available(self):
        return _env_has("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

    def plan(self, command, scene=None, frame_bgr=None):
        if self._be is None:
            from task_parser.language_backend import LLMBackend
            self._be = LLMBackend(model=self.model, logger=self._log)
        return self._be.parse(command)


# ---- 預設組裝 --------------------------------------------------------------
def default_backends(logger=None):
    return [
        GeminiVisionAdapter(logger=logger),
        ClaudeVisionAdapter(logger=logger),
        QwenLocalAdapter(logger=logger),
        OnnxVisionAdapter(logger=logger),
        ClaudePlanAdapter(logger=logger),
        RulePlanAdapter(logger=logger),
    ]


def build_default_agent(logger=None, env=None):
    """依環境（BRAIN_MODE/BRAIN_ON_PREM）組出 BrainAgent，登錄所有預設 adapter。"""
    from brain_agent.policy import Policy
    from brain_agent.registry import BackendRegistry
    from brain_agent.agent import BrainAgent
    registry = BackendRegistry(default_backends(logger=logger))
    return BrainAgent(registry, Policy.from_env(env), logger=logger)
