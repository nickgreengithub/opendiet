#!/usr/bin/env python3
"""Turn the USDA FoodData Central CSV bundles into the compact JSON the site loads.

Output per library: {"cats": [...], "foods": [[name, catIdx, kcal, p, c, fb, f, sf, sg, liquid], ...]}
All nutrient values are per 100 g (or per 100 ml for foods flagged liquid), matching FDC's basis.
"""
import csv, json, os, re, sys, collections

B = "probe/shahadsuliman_USDA-Food-DATA/dataset"
SR = "usda/srlegacy"
SURVEY = f"{B}/survey/FoodData_Central_survey_food_csv_2020-03-31"
OUT = "/home/user/opendiet/data"

# FDC nutrient ids -> the fields the table shows.
NUT = {"1008": "kcal", "1003": "p", "1005": "c", "1079": "fb",
       "1004": "f", "1258": "sf", "2000": "sg"}

# SR Legacy food_category_id -> the site's short category token.
SR_CAT = {
    1: "DAIRY", 2: "SPICES", 3: "BABY", 4: "FATS", 5: "PROTEIN", 6: "SOUPS",
    7: "PROTEIN", 8: "CEREAL", 9: "FRUIT", 10: "PROTEIN", 11: "VEGES",
    12: "NUTS", 13: "PROTEIN", 14: "DRINKS", 15: "SEAFOOD", 16: "LEGUMES",
    17: "PROTEIN", 18: "BAKED", 19: "SWEETS", 20: "GRAINS", 21: "FAST",
    22: "MEALS", 23: "SNACKS", 24: "MEALS", 25: "FAST",
}

def fndds_cat(code):
    """WWEIA category code -> the site's short category token."""
    n = int(code)
    if n < 2000: return "DAIRY"
    if n < 2400: return "PROTEIN"
    if n < 2500: return "SEAFOOD"
    if n < 2800: return "PROTEIN"
    if n < 3000: return "LEGUMES"
    if n < 4000: return "MEALS"
    if n < 4600: return "GRAINS"
    if n < 5000: return "CEREAL"
    if n < 5500: return "SNACKS"
    if n < 6000: return "SWEETS"
    if n < 6400: return "FRUIT"
    if n < 7000: return "VEGES"
    if n < 8000: return "DRINKS"
    if n < 8800: return "FATS"
    if n < 9000: return "SWEETS"
    return "BABY"

LIQUID = re.compile(
    r"\b(juice|milk|beverage|water|soda|soft drink|coffee|tea|beer|wine|liquor|"
    r"broth|cocktail|smoothie|nectar|cider|formula|drink)\b", re.I)

def is_liquid(desc, cat):
    if cat == "DRINKS":
        return 1
    # Milks and juices sit under DAIRY/FRUIT but are still measured by volume.
    return 1 if LIQUID.search(desc.split(",")[0]) else 0

# SR Legacy tacks a distribution-programme note onto many staples; it is noise in
# the name and its ALLCAPS "USDA" would trip the brand filter below.
NOTE = re.compile(r"\s*\((?:Includes|includes)[^)]*\)\s*$")

def clean(desc):
    return NOTE.sub("", desc).strip().rstrip(",")

def read_nutrients(path, keep=None):
    """fdc_id -> {field: amount} for the seven fields the table needs."""
    vals = collections.defaultdict(dict)
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            k = NUT.get(r["nutrient_id"])
            if not k:
                continue
            fid = r["fdc_id"]
            if keep is not None and fid not in keep:
                continue
            try:
                vals[fid][k] = float(r["amount"])
            except (ValueError, TypeError):
                pass
    return vals

def num(x, nd=1):
    v = round(float(x or 0), nd)
    if v < 0:
        v = 0.0
    return int(v) if v == int(v) else v

def pack(rows):
    """rows: list of (name, cat, vals, liquid) -> compact dict."""
    cats = sorted({c for _, c, _, _ in rows})
    idx = {c: i for i, c in enumerate(cats)}
    foods = []
    for name, cat, v, liq in sorted(rows, key=lambda r: r[0].lower()):
        foods.append([name, idx[cat], int(round(v.get("kcal", 0))),
                      num(v.get("p")), num(v.get("c")), num(v.get("fb")),
                      num(v.get("f")), num(v.get("sf")), num(v.get("sg")), liq])
    return {"cats": cats, "foods": foods}

def write(name, payload):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  {name:14s} {len(payload['foods']):6d} foods  "
          f"{len(payload['cats']):2d} cats  {os.path.getsize(p)/1024:8.0f} KB")

# ---------------------------------------------------------------- SR Legacy
def build_legacy():
    meta = {}
    with open(f"{SR}/food.csv", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["data_type"] != "sr_legacy_food":
                continue
            try:
                cat = SR_CAT.get(int(r["food_category_id"] or 0))
            except ValueError:
                cat = None
            if cat:
                meta[r["fdc_id"]] = (clean(r["description"]), cat)
    vals = read_nutrients(f"{SR}/food_nutrient.csv", keep=set(meta))
    rows = []
    for fid, (desc, cat) in meta.items():
        v = vals.get(fid, {})
        if not v.get("kcal"):
            continue
        rows.append((desc, cat, v, is_liquid(desc, cat)))
    return rows

# ------------------------------------------------------------------- FNDDS
def build_survey():
    desc = {}
    with open(f"{SURVEY}/food.csv", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            desc[r["fdc_id"]] = clean(r["description"])
    meta = {}
    with open(f"{SURVEY}/survey_fndds_food.csv", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            code = (r.get("wweia_category_code") or "").strip()
            if code.isdigit() and r["fdc_id"] in desc:
                meta[r["fdc_id"]] = (desc[r["fdc_id"]], fndds_cat(code))
    vals = read_nutrients(f"{SURVEY}/food_nutrient.csv", keep=set(meta))
    rows = []
    for fid, (d, cat) in meta.items():
        v = vals.get(fid, {})
        if not v.get("kcal"):
            continue
        rows.append((d, cat, v, is_liquid(d, cat)))
    return rows

# -------------------------------------------------------------------- CORE
# CORE is the everyday slice of SR Legacy: whole-food groups, generic (unbranded)
# descriptions, and not buried under a pile of preparation qualifiers.
WHOLE = {"VEGES", "FRUIT", "GRAINS", "PROTEIN", "SEAFOOD", "DAIRY", "LEGUMES", "NUTS"}
BRANDY = re.compile(r"[A-Z]{2,}|®|™|\b(Inc|Brand|Co\.|USDA Commodity)\b")

def build_core(legacy_rows):
    out = []
    for name, cat, v, liq in legacy_rows:
        if cat not in WHOLE:
            continue
        if name.count(",") > 3:
            continue
        # A brand name shows up as an ALLCAPS token or a trademark mark.
        if BRANDY.search(name):
            continue
        out.append((name, cat, v, liq))
    return out

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("building:")
    legacy = build_legacy()
    core = build_core(legacy)
    survey = build_survey()
    write("legacy.json", pack(legacy))
    write("survey.json", pack(survey))
    write("core.json", pack(core))
