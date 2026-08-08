#!/usr/bin/env python3
"""Attach one household serving to each food, from FoodData Central's portion tables.

The site measures everything per 100 g, which is the honest basis but not how anyone
eats: nobody weighs 100 g of egg. FDC publishes household measures per food — 1 medium
apple is 182 g, a slice of white bread is 29 g — and this picks the one a person would
most likely mean and writes it onto the food row as two more elements:

    [name, catIdx, kcal, p, c, fibre, fat, satfat, sugar, liquid, common, gramsPerServing, label]

Readers that stop earlier are unaffected.

    python3 tools/add_portions.py --csv <dir>            # rewrite data/*.json in place
    python3 tools/add_portions.py --csv <dir> --dry-run  # print the picks and stop

<dir> holds the FDC csv bundles: sr_legacy/ (food.csv, food_portion.csv,
sr_legacy_food.csv) and survey/ (food.csv, food_portion.csv).
"""
import argparse
import collections
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A portion has to be something you can picture. Weights and lab language are not servings.
REJECT = re.compile(
    r"guideline|yield from|cubic inch|^\s*\d*\.?\d*\s*(g|gram|grams|oz|ounce|ounces|lb|lbs|"
    r"pound|pounds|kg|ml|l|liter|litre|fl oz|fluid ounce)\s*$", re.I)

# Rough order of how naturally a shopper thinks in each unit.
PREFER = ["medium", "large", "small", "slice", "unit", "piece", "item", "whole", "each", "fruit",
          "egg", "breast", "fillet", "link", "patty", "bar", "cookie", "muffin", "roll",
          "cup", "tbsp", "tablespoon", "tsp", "teaspoon", "container", "package", "bottle",
          "can", "serving"]

AMOUNT = re.compile(r"^\s*(\d+(?:\.\d+)?|\d+/\d+)\s+")
FRACTION = re.compile(r"^(\d+)/(\d+)$")


def split_amount(desc):
    """'1 cup, sliced' -> (1.0, 'cup, sliced'). Missing amount means one."""
    m = AMOUNT.match(desc)
    if not m:
        return 1.0, desc.strip()
    raw = m.group(1)
    f = FRACTION.match(raw)
    n = (int(f.group(1)) / int(f.group(2))) if f else float(raw)
    return (n or 1.0), desc[m.end():].strip()


def rank(label):
    low = label.lower()
    for i, w in enumerate(PREFER):
        if w in low:
            return i
    return len(PREFER)


# What a serving tends to weigh, and what it tends to be worth. A head of cabbage and a
# cup of butter are both real portions and neither is a serving of anything.
LO_G, HI_G, MAX_KCAL = 10, 400, 400
# Words for the thing you buy rather than the thing you eat.
BULK = re.compile(r"\bhead|bunch|loaf|package|carton|block|jar|container|bottle|"
                  r"\bcan\b|\bbox|\bbag|whole fish|\bwheel|nlea", re.I)


def pick(portions, kcal100):
    """portions: list of (seq, amount, label, grams). Best household serving, or None."""
    best = None
    for seq, amount, label, grams in portions:
        if not label or REJECT.search(label):
            continue
        per = grams / (amount or 1)
        if per < 1 or per > 500:
            continue
        # Sane weight, then not an absurd number of calories for one sitting, then a shape
        # you eat rather than one you buy, then the more natural word, then FDC's own order.
        keyed = (0 if LO_G <= per <= HI_G else 1,
                 1 if per * kcal100 / 100 > MAX_KCAL else 0,
                 1 if BULK.search(label) else 0,
                 rank(label), seq, len(label))
        if best is None or keyed < best[0]:
            best = (keyed, round(per, 1), label)
    return best and (best[1], best[2])


def short(label):
    """'cup, sliced' -> 'CUP'. The grams carry the detail; the label only has to be read."""
    cut = re.split(r"[,(]|\s\d", label, 1)[0].strip(" .-")
    return (cut or label).upper()[:14]


def clean(desc):
    """Match the name cleaning build_data.py applies, so rows line up."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", desc).strip()


def sr_portions(csv_dir):
    d = csv_dir / "sr_legacy"
    ids = {r["fdc_id"] for r in csv.DictReader(open(d / "sr_legacy_food.csv"))}
    names = {r["fdc_id"]: r["description"]
             for r in csv.DictReader(open(d / "food.csv")) if r["fdc_id"] in ids}
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(d / "food_portion.csv")):
        if r["fdc_id"] not in names or not r["gram_weight"]:
            continue
        desc = (r["portion_description"] or "").strip() or (r["modifier"] or "").strip()
        amount = float(r["amount"]) if r["amount"] else 1.0
        n, label = split_amount(desc)
        row = (int(r["seq_num"] or 99), amount * n, label, float(r["gram_weight"]))
        for key in {names[r["fdc_id"]], clean(names[r["fdc_id"]])}:
            out[key].append(row)
    return out


def survey_portions(csv_dir):
    d = csv_dir / "survey"
    names = {r["fdc_id"]: r["description"] for r in csv.DictReader(open(d / "food.csv"))}
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(d / "food_portion.csv")):
        if r["fdc_id"] not in names or not r["gram_weight"]:
            continue
        # FNDDS writes the amount into the description and leaves the column empty.
        n, label = split_amount((r["portion_description"] or "").strip())
        row = (int(r["seq_num"] or 99), n, label, float(r["gram_weight"]))
        for key in {names[r["fdc_id"]], clean(names[r["fdc_id"]])}:
            out[key].append(row)
    return out


def apply(lib, table, dry):
    path = ROOT / "data" / f"{lib}.json"
    d = json.loads(path.read_text())
    hit = 0
    picks = {}
    for f in d["foods"]:
        while len(f) < 11:
            f.append(0)
        got = pick(table.get(f[0], []), f[2] or 0)
        if got:
            hit += 1
            picks[f[0]] = got
            grams, label = got
            f[11:] = [grams, short(label)]
        else:
            del f[11:]
    if not dry:
        path.write_text(json.dumps(d, separators=(",", ":")))
    return hit, len(d["foods"]), picks


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="directory holding sr_legacy/ and survey/")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    csv_dir = Path(args.csv)

    sr = sr_portions(csv_dir)
    sv = survey_portions(csv_dir)
    for lib, table in (("core", sr), ("legacy", sr), ("survey", sv)):
        hit, total, picks = apply(lib, table, args.dry_run)
        print(f"{lib}: {hit}/{total} foods have a serving ({round(100 * hit / total)}%)")
        if lib == "legacy":
            common = [f[0] for f in json.loads((ROOT / "data" / "legacy.json").read_text())["foods"]
                      if len(f) > 10 and f[10]]
            for n in common:
                g = picks.get(n)
                print(f"    {n[:50]:<52} {(str(g[0]) + ' g = 1 ' + short(g[1])) if g else '—'}")
    print("dry run, nothing written" if args.dry_run else "written")
