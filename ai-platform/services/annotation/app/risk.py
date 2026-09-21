"""Risk scoring per architecture doc section 3.1: risk_score = f(confidence,
demo-consistency distance) — comparing a suggested box's aspect ratio, area
ratio and screen position against the demo examples for the same class, on
top of the model's own confidence. Independent of which VLM produced the
suggestion.
"""

import statistics


def _bbox_stats(bbox_x, bbox_y, bbox_w, bbox_h, img_w, img_h):
    aspect = bbox_w / bbox_h if bbox_h else 0.0
    area_ratio = (bbox_w * bbox_h) / (img_w * img_h) if img_w and img_h else 0.0
    cx = (bbox_x + bbox_w / 2) / img_w if img_w else 0.0
    cy = (bbox_y + bbox_h / 2) / img_h if img_h else 0.0
    return {"aspect": aspect, "area_ratio": area_ratio, "cx": cx, "cy": cy}


def _z_score(value: float, samples: list[float]) -> float:
    if len(samples) < 2:
        return 0.0
    mean = statistics.mean(samples)
    stdev = statistics.pstdev(samples) or 1e-6
    return abs(value - mean) / stdev


def compute_risk_score(
    confidence: float,
    suggested: dict,
    demo_boxes: list[dict],
    img_w: int,
    img_h: int,
) -> float:
    """suggested/demo_boxes items: {bbox_x, bbox_y, bbox_w, bbox_h}."""
    suggested_stats = _bbox_stats(
        suggested["bbox_x"], suggested["bbox_y"], suggested["bbox_w"], suggested["bbox_h"], img_w, img_h
    )

    if not demo_boxes:
        inconsistency = 0.5  # no demo to compare against — treat as moderate risk
    else:
        demo_stats = [
            _bbox_stats(d["bbox_x"], d["bbox_y"], d["bbox_w"], d["bbox_h"], img_w, img_h) for d in demo_boxes
        ]
        z_scores = [
            _z_score(suggested_stats[key], [d[key] for d in demo_stats])
            for key in ("aspect", "area_ratio", "cx", "cy")
        ]
        # squash mean z-score into 0..1 via a soft cap at ~3 std devs
        inconsistency = min(1.0, sum(z_scores) / len(z_scores) / 3.0)

    risk = 0.5 * (1.0 - confidence) + 0.5 * inconsistency
    return round(max(0.0, min(1.0, risk)), 4)
