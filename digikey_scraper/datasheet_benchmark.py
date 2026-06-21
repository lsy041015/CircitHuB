from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

Region = tuple[int, int, int, int]


@dataclass(frozen=True)
class DetectionMetrics:
    precision: float
    recall: float
    matched: int
    predicted: int
    truth: int


def region_iou(a: Region, b: Region) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix0, iy0 = max(ax, bx), max(ay, by)
    ix1, iy1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(ix1 - ix0, 0) * max(iy1 - iy0, 0)
    if inter <= 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / max(union, 1)


def evaluate_detections(predicted: list[Region], truth: list[Region], iou_threshold: float = 0.5) -> DetectionMetrics:
    matched_truth: set[int] = set()
    matched = 0
    for pred in predicted:
        best_index = -1
        best_iou = 0.0
        for idx, target in enumerate(truth):
            if idx in matched_truth:
                continue
            score = region_iou(pred, target)
            if score > best_iou:
                best_iou = score
                best_index = idx
        if best_index >= 0 and best_iou >= iou_threshold:
            matched_truth.add(best_index)
            matched += 1
    precision = matched / len(predicted) if predicted else 0.0
    recall = matched / len(truth) if truth else 0.0
    return DetectionMetrics(precision, recall, matched, len(predicted), len(truth))


def load_annotation_regions(path: Path, page_number: int) -> list[Region]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for page in payload.get("pages", []):
        if int(page.get("page", 0)) != page_number:
            continue
        regions = []
        for item in page.get("regions", []):
            box = item.get("box", [])
            if len(box) == 4:
                regions.append(tuple(int(value) for value in box))
        return regions
    return []
