"""CropGuard API: detection + severity + management + outbreak forecast + cost of waiting."""
import io
import os
import sqlite3
import time

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps

import classifier
import risk
import severity
from knowledge import CROPS, KB

BASE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(BASE, "..", "frontend")
DB_PATH = os.path.join(BASE, "scans.db")
MAX_BYTES = 8 * 1024 * 1024
STAGE_MULT = {"early": 0.5, "moderate": 1.0, "severe": 1.6, "unknown": 1.0}

app = FastAPI(title="CropGuard")


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


@app.on_event("startup")
def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS scans(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, plot TEXT, crop TEXT,
            label TEXT, confidence REAL, severity REAL, stage TEXT, lat REAL, lon REAL, mode TEXT)""")


def cost_of_waiting(crop, label, stage, area, price, weeks):
    lo, hi = KB[label]["loss"]
    if hi == 0:
        return None
    mult = STAGE_MULT.get(stage, 1.0)
    yield_total = CROPS[crop]["yield_q_acre"] * area
    value = yield_total * price
    pct_lo = min(100.0, lo * mult * weeks)
    pct_hi = min(100.0, hi * mult * weeks)
    return {
        "weeks": weeks, "loss_pct": [round(pct_lo, 1), round(pct_hi, 1)],
        "loss_rupees": [round(value * pct_lo / 100), round(value * pct_hi / 100)],
        "assumptions": {"yield_q_per_acre": CROPS[crop]["yield_q_acre"], "price_per_q": price, "area_acres": area},
    }


@app.get("/api/meta")
def meta():
    return {
        "mode": classifier.mode(),
        "crops": {k: {"label": v["label"], "price_q": v["price_q"]} for k, v in CROPS.items()},
    }


@app.get("/api/risk")
def get_risk(lat: float, lon: float, crop: str):
    if crop not in CROPS:
        raise HTTPException(400, "Unknown crop")
    r = risk.forecast(lat, lon, crop)
    r["names"] = {k: KB[k]["name"] for k in r["summary"]}
    return r


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    crop: str = Form(...),
    lat: float = Form(30.9),
    lon: float = Form(75.85),
    area_acres: float = Form(1.0),
    price_per_q: float = Form(0),
    delay_weeks: float = Form(1.0),
    plot: str = Form("My field"),
):
    if crop not in CROPS:
        raise HTTPException(400, "Unknown crop")
    raw = await image.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Image too large (max 8 MB)")
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    except Exception:
        raise HTTPException(400, "Could not read image")
    img.thumbnail((1024, 1024))

    sev = severity.analyze(img)
    rk = risk.forecast(lat, lon, crop)
    risk_now = {k: v["now"] for k, v in rk["summary"].items()}
    diag = classifier.predict(img, crop, sev, risk_now)

    top = diag["top"][0]
    label = top["key"]
    kb = KB[label]
    price = price_per_q or CROPS[crop]["price_q"]
    cost = cost_of_waiting(crop, label, sev["stage"], max(area_acres, 0.01), price, max(delay_weeks, 0))

    outlook = rk["summary"].get(label)
    if sev["leaf_found"]:  # don't pollute history/map with photos that contain no leaf
        with db() as con:
            con.execute(
                "INSERT INTO scans(ts,plot,crop,label,confidence,severity,stage,lat,lon,mode) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (time.time(), plot, crop, label, top["confidence"], sev["pct"], sev["stage"], lat, lon, diag["mode"]),
            )

    return {
        "diagnosis": {**diag, "label": label, "name": kb["name"], "type": kb["type"],
                      "cause": kb["cause"], "symptoms": kb["symptoms"]},
        "severity": {k: sev[k] for k in ("leaf_found", "pct", "stage", "overlay")},
        "spread": {"rating": kb["spread"], "note": kb["spread_note"], "outlook": outlook,
                   "weather_source": rk["source"]},
        "management": {"organic": kb["organic"], "chemical": kb["chemical"], "cultural": kb["cultural"],
                       "timing": kb["timing"],
                       "disclaimer": "Confirm dose and product with the label and your local KVK/PAU advisory before spraying."},
        "cost_of_waiting": cost,
    }


@app.get("/api/scans")
def scans(limit: int = 200):
    with db() as con:
        rows = con.execute("SELECT * FROM scans ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["name"] = KB.get(d["label"], {}).get("name", d["label"])
        out.append(d)
    return out


@app.delete("/api/scans")
def clear_scans():
    with db() as con:
        con.execute("DELETE FROM scans")
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
