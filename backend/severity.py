"""Lesion severity estimation by colour segmentation (no training required).

Pixels are classified in HSV space into healthy green tissue vs. yellow / brown /
dark lesion tissue. Severity = lesion pixels / (lesion + green pixels).

Known limits (say these in your report): bare soil and dried straw look brown,
so photos should be a single leaf on a plain, non-brown background. A trained
segmentation model (e.g. U-Net) would replace this later.
"""
import base64
import io

import numpy as np
from PIL import Image


def _b64_png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def stage_for(pct: float) -> str:
    if pct < 5:
        return "early"
    if pct < 20:
        return "moderate"
    return "severe"


def analyze(img: Image.Image) -> dict:
    small = img.copy()
    small.thumbnail((512, 512))
    hsv = np.asarray(small.convert("HSV"), dtype=np.float32)
    h = hsv[..., 0] * 360.0 / 255.0
    s = hsv[..., 1] / 255.0
    v = hsv[..., 2] / 255.0

    valid = (s >= 0.15) & (v >= 0.15)  # drops white / grey / near-black background
    is_green_hue = (h >= 70) & (h <= 170)
    dark = valid & (v < 0.35) & ~is_green_hue
    green = valid & is_green_hue & ~dark
    yellow = valid & ~dark & (h >= 40) & (h < 70)
    brown = valid & ~dark & (h >= 10) & (h < 40)

    lesion = dark | yellow | brown
    leaf_px = int((lesion | green).sum())
    total_px = h.size
    if leaf_px < 0.02 * total_px:
        return {"leaf_found": False, "pct": 0.0, "stage": "unknown",
                "fractions": (0, 0, 0), "overlay": _b64_png(small)}

    lesion_px = int(lesion.sum())
    pct = 100.0 * lesion_px / leaf_px
    denom = max(lesion_px, 1)
    fractions = (yellow.sum() / denom, brown.sum() / denom, dark.sum() / denom)

    arr = np.asarray(small, dtype=np.float32).copy()
    red = np.array([230, 40, 40], dtype=np.float32)
    arr[lesion] = 0.45 * arr[lesion] + 0.55 * red
    overlay = Image.fromarray(arr.astype(np.uint8))
    return {
        "leaf_found": True,
        "pct": round(pct, 1),
        "stage": stage_for(pct),
        "fractions": tuple(float(x) for x in fractions),
        "overlay": _b64_png(overlay),
    }
