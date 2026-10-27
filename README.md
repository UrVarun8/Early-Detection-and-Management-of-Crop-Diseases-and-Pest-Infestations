# CropGuard: early detection and management of crop diseases and pests

A decision system, not just a classifier. One photo plus a location gives:

1. **What is it?** disease/pest, confidence, top-3, honest uncertainty warnings
2. **How bad?** % leaf area affected (colour segmentation) with a lesion overlay
3. **How fast will it spread?** spread rating and 7-day weather-driven outbreak risk
4. **What do I do?** organic, chemical (dose), field practices, timing
5. **What if I wait?** yield loss % and rupees for your area and price

Plus a 7-day **outbreak risk forecast** (before symptoms appear), scan history,
a Leaflet map, and Punjabi / Hindi / English UI.

## Run

```bash
cd cropguard
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd backend
uvicorn app:app --reload
```
Open http://127.0.0.1:8000 (on a phone on the same Wi-Fi: `uvicorn app:app --host 0.0.0.0` and use your PC's IP).

## Demo mode vs real mode

Out of the box there is **no trained model**, so the app runs in **demo mode**:
diagnosis is a placeholder (weather prior + lesion colour match, confidence capped
at 55%, and the UI says so). Severity, weather risk, management and cost are real.

To switch to real mode:
1. Get PlantVillage / PlantDoc images for your crops and arrange them as
   `data/train/<label>/` and `data/val/<label>/` where `<label>` is a key from
   `backend/knowledge.py` (e.g. `potato_late_blight`, `wheat_yellow_rust`).
2. `pip install torch torchvision` then `python train.py --data data --epochs 6`
3. Restart the server. It detects `backend/model/model.pt` and enables the
   classifier plus Grad-CAM heatmap automatically.

## Files

| File | Role |
|---|---|
| `backend/app.py` | FastAPI routes, SQLite history, cost-of-waiting |
| `backend/classifier.py` | Real (MobileNetV2 + Grad-CAM) and demo diagnosis |
| `backend/severity.py` | HSV lesion segmentation, % severity, overlay |
| `backend/risk.py` | Open-Meteo weather, per-disease risk scoring, 7-day forecast |
| `backend/knowledge.py` | Disease facts, treatments, weather rules (edit to add diseases) |
| `frontend/index.html` | Mobile-first UI, i18n, map |
| `train.py` | Transfer-learning training script |

## Things to say honestly in your report

- Weather risk rules are simplified from published favourable conditions; they are
  not validated against outbreak records. Say so, and list that as future work.
- Severity by colour fails on brown soil/straw backgrounds. Future work: U-Net.
- Models trained on PlantVillage drop sharply on real field photos. Report accuracy
  on PlantDoc or your own field photos separately.
- Doses are from common Indian extension recommendations; verify with PAU / KVK.
- Punjabi/Hindi strings should be reviewed by a native speaker.
