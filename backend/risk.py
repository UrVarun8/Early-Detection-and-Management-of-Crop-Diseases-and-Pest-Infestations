"""Weather-driven outbreak risk forecast (the 'early' in early detection).

Each disease has a favourable temperature band and humidity band (knowledge.py).
Daily raw risk = temp suitability x humidity suitability x wetness factor.
A small carry-over from the previous day models how infection pressure builds
up when favourable weather persists.

Weather comes from Open-Meteo (free, no key). If the request fails (offline,
blocked), a clearly-flagged simulated winter-Punjab series is used so the app
still runs for demos. The API response always says which source was used.
"""
import datetime as dt
import math
import random
import time

import httpx

from knowledge import KB, diseases_for

_CACHE: dict = {}
CACHE_SECONDS = 30 * 60


def _trap(x, a, b, c, d):
    if x <= a or x >= d:
        return 0.0
    if x < b:
        return (x - a) / (b - a)
    if x <= c:
        return 1.0
    return (d - x) / (d - c)


def _ramp(x, lo, hi):
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def level_for(score: float) -> str:
    if score < 30:
        return "low"
    if score < 60:
        return "moderate"
    if score < 80:
        return "high"
    return "severe"


def _fetch_weather(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation",
        "past_days": 2, "forecast_days": 7, "timezone": "auto",
    }
    r = httpx.get(url, params=params, timeout=8)
    r.raise_for_status()
    hr = r.json()["hourly"]
    days: dict = {}
    for t, temp, rh, pr in zip(hr["time"], hr["temperature_2m"], hr["relative_humidity_2m"], hr["precipitation"]):
        if temp is None or rh is None:
            continue
        d = t[:10]
        e = days.setdefault(d, {"t": [], "rh": [], "rain": 0.0})
        e["t"].append(temp)
        e["rh"].append(rh)
        e["rain"] += pr or 0.0
    out = []
    for d in sorted(days):
        e = days[d]
        out.append({"date": d, "tmean": round(sum(e["t"]) / len(e["t"]), 1),
                    "rh": round(sum(e["rh"]) / len(e["rh"])), "rain": round(e["rain"], 1)})
    return out


def _simulate_weather():
    rnd = random.Random(dt.date.today().toordinal())
    out = []
    start = dt.date.today() - dt.timedelta(days=2)
    base_t = 17.0
    for i in range(9):
        d = start + dt.timedelta(days=i)
        t = base_t + rnd.uniform(-3, 3)
        rh = rnd.uniform(60, 92)
        rain = rnd.choice([0, 0, 0, 1.2, 4.0]) if rh > 80 else 0
        out.append({"date": d.isoformat(), "tmean": round(t, 1), "rh": round(rh), "rain": rain})
    return out


def get_weather(lat: float, lon: float):
    key = (round(lat, 2), round(lon, 2))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1], hit[2]
    try:
        data, source = _fetch_weather(lat, lon), "open-meteo"
    except Exception:
        data, source = _simulate_weather(), "simulated"
    _CACHE[key] = (time.time(), data, source)
    return data, source


def _raw(rule, day):
    ft = _trap(day["tmean"], *rule["temp"])
    fr = _ramp(day["rh"], *rule["rh"])
    if rule.get("rh_invert"):
        fr = 1.0 - fr
    wet = 1.0 if day["rain"] >= 1.0 else (0.6 if day["rh"] >= 90 else 0.0)
    w = rule.get("wet", 0.3)
    return 100.0 * ft * fr * ((1 - w) + w * wet) if w < 1 else 100.0 * ft * fr * wet


def forecast(lat: float, lon: float, crop: str) -> dict:
    weather, source = get_weather(lat, lon)
    today = dt.date.today().isoformat()
    keys = diseases_for(crop)
    prev = {k: 0.0 for k in keys}
    rows = []
    for day in weather:
        risks = {}
        for k in keys:
            raw = _raw(KB[k]["weather"], day)
            score = 0.65 * raw + 0.35 * prev[k]
            prev[k] = score
            risks[k] = round(score)
        rows.append({**day, "risks": risks})
    forecast_rows = [r for r in rows if r["date"] >= today] or rows[-7:]

    summary = {}
    for k in keys:
        series = [(r["date"], r["risks"][k]) for r in forecast_rows]
        peak_date, peak = max(series, key=lambda x: x[1])
        now = forecast_rows[0]["risks"][k]
        summary[k] = {
            "name": KB[k]["name"], "now": now, "now_level": level_for(now),
            "peak": peak, "peak_date": peak_date, "peak_level": level_for(peak),
        }
    return {"source": source, "crop": crop, "days": forecast_rows, "summary": summary}
