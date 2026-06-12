#!/usr/bin/env python3
"""
本地 Qwen2.5-VL 開放詞彙偵測後端（**全機載、不上雲**）。

Robot_C 整合 Phase A1：作為雲端 api_backend / gemini_backend 的本地替代，在 AGX Orin
上以 Qwen2.5-VL 做開放詞彙物品分類/偵測，輸出與其他後端**完全相同**的 dict 形
（{class, score, cx, cy, w, h, depth} in pixels，重用 perception.api_backend.parse_detections），
所以下游（perception_node -> /perception/objects -> world_model/planner）完全不變。

不上雲：模型在本機推論、無對外 API 呼叫。注意首次載入權重會從 HuggingFace 下載——
production 須事先把權重放到本地路徑並設 `HF_HUB_OFFLINE=1`，`QWEN_MODEL` 指向本地目錄。

延遲匯入：torch / transformers / cv2 只在實際建構 detector 時才載入，因此本模組與其
**純解析器**（build_prompt / parse_qwen_text）可在無 GPU/無這些套件的開發機上 import 與單元測試。

環境變數：QWEN_MODEL（預設 Qwen/Qwen2.5-VL-7B-Instruct）、QWEN_DEVICE（預設 cuda）、
QWEN_MAX_TOKENS（預設 512）。任何載入/推論錯誤 -> detect() 回 []（perception_node 退回 ONNX）。
"""

import json
import os
import re

from perception.api_backend import parse_detections

DEFAULT_MODEL = os.environ.get("QWEN_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")

_PROMPT = (
    "You are an open-vocabulary object detector. Detect the physical objects in "
    "the image, paying special attention to: {hints}. Respond ONLY with JSON of "
    "this exact shape:\n"
    '{{"detections": [{{"label": "<lowercase name>", "confidence": <0..1>, '
    '"cx": <0..1>, "cy": <0..1>, "w": <0..1>, "h": <0..1>, "depth_m": <metres>}}]}}\n'
    "cx,cy,w,h are the bounding-box centre and size NORMALIZED to the image "
    "(0..1), origin top-left. depth_m is the estimated distance from the camera "
    "in metres. Return an empty list if nothing relevant is visible."
)


def build_prompt(hints):
    """Pure: 組出給 Qwen 的文字提示（與 gemini/claude 後端相同的 JSON 契約）。"""
    hint_str = ", ".join(hints) if hints else "any nameable object"
    return _PROMPT.format(hints=hint_str)


def _extract_json(text):
    """從模型輸出文字抽出 JSON 物件（容忍 ```json 圍欄與前後雜訊）。"""
    if not isinstance(text, str):
        return None
    t = text.strip()
    # 去掉 ```json ... ``` 圍欄
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", t, re.DOTALL)
    if fence:
        t = fence.group(1).strip()
    # 取第一個 { 到最後一個 } 之間（避免尾隨說明文字）
    if "{" in t and "}" in t:
        t = t[t.find("{"): t.rfind("}") + 1]
    try:
        return json.loads(t)
    except (ValueError, TypeError):
        return None


def parse_qwen_text(raw_text, frame_w, frame_h, conf_thresh=0.3):
    """Pure: Qwen 文字輸出 -> 像素偵測 dict（重用 parse_detections）。

    raw_text: 模型產生的文字（含/不含 ```json 圍欄）。malformed -> []。
    """
    tool_input = _extract_json(raw_text)
    if tool_input is None:
        return []
    return parse_detections(tool_input, frame_w, frame_h, conf_thresh=conf_thresh)


class QwenVLDetector:
    """以本地 Qwen2.5-VL 做開放詞彙偵測；detect() 出錯一律回 []（讓 perception_node 退回 ONNX）。"""

    def __init__(self, model=None, conf_thresh=0.3, max_tokens=None,
                 device=None, logger=None):
        self.model_id = model or DEFAULT_MODEL
        self.conf_thresh = conf_thresh
        self.max_tokens = int(max_tokens or os.environ.get("QWEN_MAX_TOKENS", 512))
        self.device = device or os.environ.get("QWEN_DEVICE", "cuda")
        self._log = logger
        # 延遲匯入重型相依（torch/transformers）——只有真正用本後端時才需要。
        from transformers import (
            Qwen2_5_VLForConditionalGeneration, AutoProcessor,
        )
        import torch
        self._torch = torch
        dtype = torch.float16 if self.device.startswith("cuda") else torch.float32
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_id, torch_dtype=dtype, device_map=self.device)
        self.processor = AutoProcessor.from_pretrained(self.model_id)

    def _warn(self, msg):
        if self._log:
            self._log.warn(msg)

    def detect(self, frame_bgr, class_hints=None):
        """frame_bgr: HxWx3 BGR ndarray。回傳像素偵測 dict list；任何錯誤 -> []。"""
        try:
            import cv2
            from PIL import Image
            h, w = frame_bgr.shape[:2]
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": build_prompt(class_hints)},
                ],
            }]
            text = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True)
            inputs = self.processor(text=[text], images=[image],
                                    return_tensors="pt").to(self.device)
            with self._torch.no_grad():
                out_ids = self.model.generate(**inputs, max_new_tokens=self.max_tokens,
                                              do_sample=False)
            trimmed = out_ids[:, inputs.input_ids.shape[1]:]
            raw = self.processor.batch_decode(
                trimmed, skip_special_tokens=True,
                clean_up_tokenization_spaces=False)[0]
        except Exception as e:  # noqa: BLE001 — 載入/推論任何失敗都退回空
            self._warn(f"Qwen-VL detect failed: {e}")
            return []
        return parse_qwen_text(raw, w, h, conf_thresh=self.conf_thresh)
