#!/usr/bin/env python3
"""
YOLOv8 detection decoding (pure numpy, no cv2/ROS — unit-testable on host).

detection_v2.onnx is a YOLOv8 model: input (1,3,S,S), output (1, 4+nc, A) where
the first 4 rows are box (cx,cy,w,h) in input-pixel coords and the remaining nc
rows are per-class scores; A is the anchor count. The OLD perception postprocess
assumed per-row [x,y,w,h,conf,cls] and produced garbage on this layout — this
module decodes it correctly (transpose -> per-anchor argmax -> scale -> NMS).
"""

import numpy as np


def _to_anchors_by_channels(out):
    """Normalise model output to (num_anchors, 4+nc)."""
    a = np.asarray(out, dtype=np.float32)
    if a.ndim == 3:
        a = a[0]
    if a.ndim != 2:
        a = a.reshape(a.shape[0], -1)
    # YOLOv8 export is (4+nc, anchors); 4+nc is small, anchors large -> transpose.
    if a.shape[0] < a.shape[1]:
        a = a.T
    return a  # (num_anchors, 4+nc)


def _nms_numpy(boxes_xyxy, scores, iou_thresh):
    """Class-agnostic NMS. boxes_xyxy: (M,4); scores: (M,). Returns kept indices."""
    if len(boxes_xyxy) == 0:
        return []
    x1, y1, x2, y2 = boxes_xyxy[:, 0], boxes_xyxy[:, 1], boxes_xyxy[:, 2], boxes_xyxy[:, 3]
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(x1[i], x1[rest]); yy1 = np.maximum(y1[i], y1[rest])
        xx2 = np.minimum(x2[i], x2[rest]); yy2 = np.minimum(y2[i], y2[rest])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        iou = inter / (areas[i] + areas[rest] - inter + 1e-9)
        order = rest[iou < iou_thresh]
    return keep


def decode_yolov8(out, frame_w, frame_h, input_size=224,
                  conf_thresh=0.5, iou_thresh=0.45, class_names=None):
    """Decode a YOLOv8 ONNX output into a list of detections in frame pixels.

    Returns: list of {class, score, cx, cy, w, h} (cx,cy,w,h in frame pixels).
    """
    pred = _to_anchors_by_channels(out)
    if pred.shape[1] <= 4:
        return []
    boxes = pred[:, :4]                       # cx,cy,w,h in input_size px
    cls_scores = pred[:, 4:]
    conf = cls_scores.max(axis=1)
    cls_id = cls_scores.argmax(axis=1)

    keep = conf >= conf_thresh
    if not np.any(keep):
        return []
    boxes, conf, cls_id = boxes[keep], conf[keep], cls_id[keep]

    sx, sy = frame_w / float(input_size), frame_h / float(input_size)
    cx = boxes[:, 0] * sx; cy = boxes[:, 1] * sy
    w = boxes[:, 2] * sx; h = boxes[:, 3] * sy
    xyxy = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)

    # Class-aware NMS: offset boxes by class id so different classes never
    # overlap in NMS space (otherwise a pen lying on a box would be suppressed).
    offset = cls_id.astype(np.float32) * (max(frame_w, frame_h) + 1.0)
    xyxy_nms = xyxy + offset[:, None]

    dets = []
    for i in _nms_numpy(xyxy_nms, conf, iou_thresh):
        ci = int(cls_id[i])
        name = class_names[ci] if (class_names and ci < len(class_names)) else str(ci)
        dets.append({"class": name, "score": float(conf[i]),
                     "cx": float(cx[i]), "cy": float(cy[i]),
                     "w": float(w[i]), "h": float(h[i])})
    return dets
