"""Diagnosis engine with two modes.

REAL mode  - used automatically when backend/model/model.pt and labels.json exist
             (produced by train.py). MobileNetV2 transfer-learning classifier,
             restricted to the selected crop, with a Grad-CAM heatmap.

DEMO mode  - used when no trained model is present. This is NOT a trained
             classifier. It ranks the selected crop's diseases using
             (a) current weather risk as a prior and (b) how well the lesion
             colours match each disease. Confidence is capped and the UI says
             so. It exists so the full pipeline can be demonstrated before
             you have trained a model.
"""
import base64
import io
import json
import os

import numpy as np
from PIL import Image

from knowledge import KB, diseases_for

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pt")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.json")
LOW_CONF = 0.60

_real = None  # lazily loaded (model, labels, transform, torch)


def mode() -> str:
    return "real" if os.path.exists(MODEL_PATH) and os.path.exists(LABELS_PATH) else "demo"


def _top(items, n=3):
    items = sorted(items, key=lambda x: -x["confidence"])[:n]
    for it in items:
        it["name"] = KB[it["key"]]["name"]
    return items


# ---------------------------------------------------------------- demo mode
def _demo(crop, sev, risk_now):
    keys = diseases_for(crop)
    healthy_key = f"{crop}_healthy"
    if not sev.get("leaf_found"):
        return {"mode": "demo", "top": _top([{"key": healthy_key, "confidence": 0.2}]),
                "uncertain": True, "reason": "no_leaf", "heatmap": None}
    if sev["pct"] < 3:
        c = min(0.55, 0.45 + (3 - sev["pct"]) / 10)
        items = [{"key": healthy_key, "confidence": c}] + \
                [{"key": k, "confidence": (1 - c) / len(keys)} for k in keys]
        return {"mode": "demo", "top": _top(items), "uncertain": True, "reason": "demo", "heatmap": None}

    obs = sev["fractions"]
    scores = {}
    for k in keys:
        prof = KB[k]["lesion"]
        match = 1.0 - 0.5 * sum(abs(a - b) for a, b in zip(prof, obs))
        prior = 0.2 + 0.8 * (risk_now.get(k, 0) / 100.0)
        scores[k] = prior * (0.3 + max(match, 0))
    total = sum(scores.values()) or 1.0
    items = [{"key": k, "confidence": min(0.55, v / total)} for k, v in scores.items()]
    return {"mode": "demo", "top": _top(items), "uncertain": True, "reason": "demo", "heatmap": None}


# ---------------------------------------------------------------- real mode
def _load_real():
    global _real
    if _real is not None:
        return _real
    import torch
    from torchvision import models, transforms

    labels = json.load(open(LABELS_PATH))
    model = models.mobilenet_v2(weights=None)
    model.classifier[1] = torch.nn.Linear(model.last_channel, len(labels))
    model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    model.eval()
    tf = transforms.Compose([
        transforms.Resize((224, 224)), transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    _real = (model, labels, tf, torch)
    return _real


def _real_predict(img, crop):
    model, labels, tf, torch = _load_real()
    x = tf(img).unsqueeze(0)
    acts, grads = {}, {}
    layer = model.features[-1]

    def fwd(_m, _i, o):
        acts["a"] = o
        o.register_hook(lambda g: grads.update(g=g))

    h = layer.register_forward_hook(fwd)
    logits = model(x)[0]
    h.remove()

    allowed = [i for i, k in enumerate(labels) if k.startswith(crop + "_")]
    if not allowed:
        allowed = list(range(len(labels)))
    mask = torch.full_like(logits, float("-inf"))
    mask[allowed] = 0
    probs = torch.softmax(logits + mask, dim=0)
    idx = int(probs.argmax())

    model.zero_grad()
    logits[idx].backward()
    w = grads["g"].mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((w * acts["a"]).sum(1, keepdim=True))
    cam = torch.nn.functional.interpolate(cam, size=img.size[::-1], mode="bilinear", align_corners=False)[0, 0]
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    cam = cam.detach().numpy()

    base = np.asarray(img.resize(img.size), dtype=np.float32)
    heat = np.stack([cam * 255, cam * 180, (1 - cam) * 60], axis=-1)
    blend = (0.55 * base + 0.45 * heat).astype(np.uint8)
    out = Image.fromarray(blend)
    out.thumbnail((512, 512))
    buf = io.BytesIO()
    out.save(buf, format="PNG")

    items = [{"key": labels[i], "confidence": float(probs[i])} for i in allowed if labels[i] in KB]
    top = _top(items)
    return {"mode": "real", "top": top, "uncertain": top[0]["confidence"] < LOW_CONF,
            "reason": "low_confidence" if top[0]["confidence"] < LOW_CONF else None,
            "heatmap": base64.b64encode(buf.getvalue()).decode()}


def predict(img, crop, sev, risk_now):
    if mode() == "real":
        return _real_predict(img, crop)
    return _demo(crop, sev, risk_now)
