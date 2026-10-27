"""Knowledge base: disease/pest facts, management plans, weather rules.

Doses follow commonly published Indian extension recommendations (ICAR / state
agricultural universities). They are a starting point: always check the product
label and confirm with your local KVK / PAU advisory before spraying.

weather rule:
  temp = (a, b, c, d) trapezoid: 0 below a, ramps to 1 at b, stays 1 until c, ramps to 0 at d (deg C)
  rh   = (lo, hi) relative humidity ramp, %
  rh_invert = True for pests that prefer drier air
  wet  = weight given to rain / leaf-wetness
lesion = expected share of (yellow, brown, dark) among lesion pixels, used by demo mode only.
loss   = rough untreated yield loss per week (low %, high %) at moderate severity; planning estimate.
"""

CROPS = {
    "wheat": {"label": "Wheat", "yield_q_acre": 20, "price_q": 2400},
    "rice": {"label": "Rice (paddy)", "yield_q_acre": 25, "price_q": 2300},
    "potato": {"label": "Potato", "yield_q_acre": 100, "price_q": 1200},
    "tomato": {"label": "Tomato", "yield_q_acre": 120, "price_q": 1500},
}

KB = {
    "wheat_yellow_rust": {
        "crop": "wheat", "name": "Yellow (stripe) rust", "type": "disease",
        "cause": "Fungus Puccinia striiformis",
        "symptoms": "Yellow-orange powdery stripes along leaf veins; leaves dry out early.",
        "spread": 5, "spread_note": "Spores travel by wind over long distances; can cover a district within 1-2 weeks in cool, foggy weather.",
        "loss": (3, 8),
        "organic": ["Rogue out volunteer wheat and infected patches early", "Grow rust-resistant varieties recommended by PAU next season"],
        "chemical": [
            {"name": "Propiconazole 25% EC", "dose": "1 ml per litre of water", "note": "Spray at first stripes; repeat after ~15 days if the weather stays cool and humid"},
            {"name": "Tebuconazole 25.9% EC", "dose": "1 ml per litre of water", "note": "Alternative; rotate active ingredients"},
        ],
        "cultural": ["Scout fields weekly from December, especially border rows", "Avoid excess nitrogen"],
        "timing": "Spray within 2-3 days of confirming stripes, in a dry window (not before rain).",
        "weather": {"temp": (2, 7, 15, 20), "rh": (65, 85), "wet": 0.5},
        "lesion": (0.8, 0.15, 0.05),
    },
    "wheat_powdery_mildew": {
        "crop": "wheat", "name": "Powdery mildew", "type": "disease",
        "cause": "Fungus Blumeria graminis",
        "symptoms": "White powdery patches on leaves and stems that turn grey-brown with age.",
        "spread": 3, "spread_note": "Spreads by wind-blown spores; dense, heavily fertilised crops are hit hardest.",
        "loss": (2, 5),
        "organic": ["Wettable sulphur 80% WP at 2.5-3 g per litre (permitted in organic systems)"],
        "chemical": [{"name": "Propiconazole 25% EC", "dose": "1 ml per litre of water", "note": "One spray at first appearance"}],
        "cultural": ["Use recommended seed rate; avoid over-dense sowing", "Avoid excess nitrogen"],
        "timing": "Spray when patches first appear on lower leaves.",
        "weather": {"temp": (10, 15, 22, 28), "rh": (50, 80), "wet": 0.1},
        "lesion": (0.3, 0.4, 0.3),
    },
    "wheat_aphid": {
        "crop": "wheat", "name": "Aphids (wheat)", "type": "pest",
        "cause": "Sap-sucking insects (Sitobion / Rhopalosiphum spp.)",
        "symptoms": "Clusters of small green/black insects on leaves and ear heads, sticky honeydew, yellowing.",
        "spread": 4, "spread_note": "Populations can double in a few days in mild, dry-ish, cloudy weather.",
        "loss": (2, 6),
        "organic": ["Neem seed kernel extract 5% spray", "Conserve ladybird beetles and lacewings; avoid unnecessary broad-spectrum sprays"],
        "chemical": [{"name": "Imidacloprid 17.8% SL", "dose": "0.3 ml per litre of water", "note": "Only if aphids cross the local economic threshold"}],
        "cultural": ["Avoid late sowing", "Scout 20 tillers across the field, not just the border"],
        "timing": "Act when counts keep rising, not on the first few aphids.",
        "weather": {"temp": (8, 15, 25, 32), "rh": (30, 60), "wet": 0.0, "rh_invert": True},
        "lesion": (0.7, 0.2, 0.1),
    },
    "rice_blast": {
        "crop": "rice", "name": "Rice blast", "type": "disease",
        "cause": "Fungus Magnaporthe oryzae",
        "symptoms": "Diamond-shaped spots with grey centres and brown borders on leaves; neck rot at heading.",
        "spread": 4, "spread_note": "Spore release peaks on humid, cloudy nights with dew; heavy nitrogen makes plants more susceptible.",
        "loss": (4, 10),
        "organic": ["Pseudomonas fluorescens: seed treatment 10 g/kg and foliar spray 5-10 g per litre", "Balanced nitrogen in split doses"],
        "chemical": [
            {"name": "Tricyclazole 75% WP", "dose": "0.6 g per litre of water", "note": "Spray at first leaf spots; repeat at heading if weather stays humid"},
            {"name": "Isoprothiolane 40% EC", "dose": "1.5 ml per litre of water", "note": "Alternative"},
        ],
        "cultural": ["Avoid excess nitrogen", "Keep bunds clean of weeds"],
        "timing": "Protect the crop at tillering and again at booting/heading.",
        "weather": {"temp": (15, 22, 28, 32), "rh": (80, 93), "wet": 0.5},
        "lesion": (0.15, 0.55, 0.3),
    },
    "rice_bacterial_blight": {
        "crop": "rice", "name": "Bacterial leaf blight", "type": "disease",
        "cause": "Bacterium Xanthomonas oryzae pv. oryzae",
        "symptoms": "Water-soaked streaks starting at leaf tips that turn yellow, then straw-coloured.",
        "spread": 4, "spread_note": "Spreads through irrigation water, rain splash and wind; flooding or storms trigger outbreaks.",
        "loss": (5, 12),
        "organic": ["Drain the field temporarily", "Avoid clipping seedling tips at transplanting"],
        "chemical": [{"name": "Streptocycline + copper oxychloride", "dose": "0.15 g + 2.5 g per litre of water", "note": "Limited effect once severe; best used early"}],
        "cultural": ["Do not apply extra nitrogen when symptoms show", "Do not move irrigation water from infected to clean fields"],
        "timing": "Act at first streaks; late sprays give little recovery.",
        "weather": {"temp": (22, 26, 32, 36), "rh": (75, 90), "wet": 0.6},
        "lesion": (0.55, 0.3, 0.15),
    },
    "potato_late_blight": {
        "crop": "potato", "name": "Late blight", "type": "disease",
        "cause": "Oomycete Phytophthora infestans",
        "symptoms": "Dark water-soaked blotches on leaves with pale rim, white fuzz underneath in humid air; rapid collapse of haulms.",
        "spread": 5, "spread_note": "Can destroy a field in 7-10 days when nights are cool and wet. Prevention matters more than cure.",
        "loss": (10, 30),
        "organic": ["Copper oxychloride 50% WP at 3 g per litre as a preventive spray", "Destroy infected haulms; do not leave culled tubers in heaps"],
        "chemical": [
            {"name": "Mancozeb 75% WP (preventive)", "dose": "2.5 g per litre of water", "note": "Before symptoms, when forecast risk is high; repeat every 7-10 days"},
            {"name": "Cymoxanil + Mancozeb (curative)", "dose": "3 g per litre of water", "note": "Once blight is present; alternate with other chemistries to avoid resistance"},
        ],
        "cultural": ["Earthing-up to protect tubers", "Cut haulms 10-15 days before harvest if blight is present"],
        "timing": "Spray BEFORE forecast cool, humid, rainy spells. After rain washes protectant off, re-spray.",
        "weather": {"temp": (6, 10, 22, 27), "rh": (75, 92), "wet": 0.4},
        "lesion": (0.1, 0.4, 0.5),
    },
    "potato_early_blight": {
        "crop": "potato", "name": "Early blight", "type": "disease",
        "cause": "Fungus Alternaria solani",
        "symptoms": "Brown spots with concentric rings (target pattern) on older leaves first.",
        "spread": 3, "spread_note": "Slower than late blight; stressed or nutrient-poor plants are more affected.",
        "loss": (3, 10),
        "organic": ["Copper-based fungicide", "Trichoderma-enriched compost in soil"],
        "chemical": [{"name": "Mancozeb 75% WP", "dose": "2.5 g per litre of water", "note": "Repeat at 10-14 day intervals while conditions favour disease"}],
        "cultural": ["Crop rotation (2-3 years away from potato/tomato)", "Balanced fertiliser, adequate irrigation"],
        "timing": "Start at first lesions on lower leaves.",
        "weather": {"temp": (15, 24, 30, 35), "rh": (60, 85), "wet": 0.3},
        "lesion": (0.2, 0.6, 0.2),
    },
    "tomato_early_blight": {
        "crop": "tomato", "name": "Early blight", "type": "disease",
        "cause": "Fungus Alternaria solani",
        "symptoms": "Dark spots with concentric rings on lower leaves, yellow halo, leaf drop; stem and fruit lesions.",
        "spread": 3, "spread_note": "Warm, humid weather with dew speeds it up.",
        "loss": (5, 15),
        "organic": ["Trichoderma soil application", "Neem oil 3 ml per litre as a mild protectant"],
        "chemical": [{"name": "Mancozeb 75% WP", "dose": "2.5 g per litre of water", "note": "Repeat every 10-14 days"}],
        "cultural": ["Stake plants and mulch to stop soil splash", "Remove infected lower leaves"],
        "timing": "Begin at first spots; keep foliage dry (drip irrigation if possible).",
        "weather": {"temp": (15, 24, 29, 35), "rh": (60, 85), "wet": 0.3},
        "lesion": (0.2, 0.6, 0.2),
    },
    "tomato_late_blight": {
        "crop": "tomato", "name": "Late blight", "type": "disease",
        "cause": "Oomycete Phytophthora infestans",
        "symptoms": "Greasy grey-green blotches on leaves and stems; firm brown patches on fruit.",
        "spread": 5, "spread_note": "Explosive in cool, wet weather.",
        "loss": (10, 30),
        "organic": ["Copper oxychloride as a preventive", "Remove and destroy infected plants"],
        "chemical": [{"name": "Cymoxanil + Mancozeb", "dose": "3 g per litre of water", "note": "Alternate chemistries to avoid resistance"}],
        "cultural": ["Wider spacing and airflow", "Avoid overhead irrigation"],
        "timing": "Preventive before cool, wet spells; curative at first lesions.",
        "weather": {"temp": (8, 12, 22, 26), "rh": (80, 92), "wet": 0.5},
        "lesion": (0.1, 0.35, 0.55),
    },
}

for _crop, _c in CROPS.items():
    KB[f"{_crop}_healthy"] = {
        "crop": _crop, "name": "Healthy / no clear disease", "type": "healthy",
        "cause": "-", "symptoms": "No significant lesions detected.",
        "spread": 0, "spread_note": "", "loss": (0, 0),
        "organic": [], "chemical": [], "cultural": ["Keep scouting weekly and watch the weather forecast tab."],
        "timing": "", "weather": None, "lesion": (0, 0, 0),
    }


def diseases_for(crop, include_healthy=False):
    return [k for k, d in KB.items()
            if d["crop"] == crop and (include_healthy or d["type"] != "healthy")]
