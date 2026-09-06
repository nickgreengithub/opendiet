#!/usr/bin/env python3
"""Add what the rest of 100 g is made of, so a food can be drawn rather than only listed.

Protein, carbohydrate and fat are what the table shows, but they are a minority of most
foods by weight: the median food in SR Legacy is 64% water. FDC publishes the remainder, and
because carbohydrate is reported *by difference* — 100 minus everything else — these six
sum to 100 g exactly:

    water + protein + carbohydrate + fat + ash + alcohol = 100

This appends the parts the site did not already have, plus the two fats needed to break the
fat figure down, as five more elements on each food row:

    [ ..., servingGrams, servingLabel, water, ash, mufa, pufa, alcohol, trans ]

Readers that stop earlier are unaffected — the root site reads the first ten.

    python3 tools/add_composition.py --csv <dir>
    python3 tools/add_composition.py --csv <dir> --dry-run

<dir> holds the FDC csv bundles: sr_legacy/ and survey/, as for add_portions.py.
"""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# FDC nutrient ids. Ash is the mineral residue: no energy, but it has to be accounted for or
# the parts do not reach 100 — table salt is 99.8% of it.
NUT = {"1051": "water", "1007": "ash", "1292": "mufa", "1293": "pufa", "1018": "alcohol",
       "1257": "trans"}
# The order they are written onto the row. Trans is last so every earlier reader's indices
# hold still.
ORDER = ["water", "ash", "mufa", "pufa", "alcohol", "trans"]


def clean(desc):
    """Match the name cleaning build_data.py applies, so rows line up."""
    import re
    return re.sub(r"\s*\([^)]*\)\s*$", "", desc).strip()


def read(csv_dir, sub, only=None):
    d = csv_dir / sub
    names = {r["fdc_id"]: r["description"] for r in csv.DictReader(open(d / "food.csv"))
             if only is None or r["fdc_id"] in only}
    out = {}
    for r in csv.DictReader(open(d / "food_nutrient.csv")):
        if r["nutrient_id"] not in NUT or r["fdc_id"] not in names:
            continue
        amount = (r["amount"] or "").strip()
        if not amount:
            continue      # no row and no figure both mean nobody measured, not none of it
        for key in {names[r["fdc_id"]], clean(names[r["fdc_id"]])}:
            out.setdefault(key, {})[NUT[r["nutrient_id"]]] = float(amount)
    return out


def sr(csv_dir):
    d = csv_dir / "sr_legacy"
    ids = {r["fdc_id"] for r in csv.DictReader(open(d / "sr_legacy_food.csv"))}
    return read(csv_dir, "sr_legacy", ids)


def trim(x):
    """Keep the file honest about its precision: one decimal is more than the source has."""
    return int(x) if x == int(x) else round(x, 1)


# The figures this step owns that FDC only writes where somebody measured them.
REQUIRED = ("water", "ash", "mufa", "pufa")


def apply(lib, table, dry, keep_incomplete=False):
    path = ROOT / "data" / f"{lib}.json"
    d = json.loads(path.read_text())
    got = 0
    drop = []
    for f in d["foods"]:
        while len(f) < 13:
            f.append(0)
        v = table.get(f[0], {})
        if v:
            got += 1
        p, c, fat = f[3], f[4], f[6]
        water = v.get("water")
        # FNDDS does not publish ash, so it is what is left once everything else is counted.
        # Never below zero: a rounding shortfall is not a mineral. It can only be worked out
        # where the figures it is worked out from are all there.
        if "ash" in v:
            ash = v["ash"]
        elif water is None or None in (p, c, fat):
            ash = None
        else:
            ash = max(0.0, 100 - water - p - c - fat - (v.get("alcohol") or 0.0))
        # Alcohol and trans fat are the two FDC leaves out of a food that has none of them
        # rather than only of a food nobody tested, so absent reads as zero for those two.
        vals = {"water": water, "ash": ash, "mufa": v.get("mufa"), "pufa": v.get("pufa"),
                "alcohol": v.get("alcohol", 0.0), "trans": v.get("trans", 0.0)}
        if not keep_incomplete and any(vals[k] is None for k in REQUIRED):
            drop.append(f)
            continue
        f[13:] = [None if vals[k] is None else trim(vals[k]) for k in ORDER]
    if drop:
        gone = {id(f) for f in drop}
        d["foods"] = [f for f in d["foods"] if id(f) not in gone]
    if not dry:
        path.write_text(json.dumps(d, separators=(",", ":")))
    return got, len(d["foods"]), len(drop)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="directory holding sr_legacy/ and survey/")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-incomplete", action="store_true",
                    help="keep a food whose water or fat breakdown nobody measured, and "
                         "write null for it, instead of leaving the food out")
    args = ap.parse_args()
    csv_dir = Path(args.csv)

    tables = {"core": sr(csv_dir), "survey": read(csv_dir, "survey")}
    tables["legacy"] = tables["core"]
    for lib in ("core", "legacy", "survey"):
        got, total, gone = apply(lib, tables[lib], args.dry_run, args.keep_incomplete)
        short = f", {gone} left out for want of a figure" if gone else ""
        print(f"{lib}: {got}/{total} foods matched to FDC "
              f"({round(100 * got / total)}%){short}")

    d = json.loads((ROOT / "data" / "legacy.json").read_text())
    off = [f for f in d["foods"] if abs(f[13] + f[3] + f[4] + f[6] + f[14] + f[17] - 100) > 1.5]
    print(f"legacy: {len(off)} of {len(d['foods'])} foods whose parts miss 100 g by more than 1.5 g")
    for f in off[:5]:
        print(f"    {f[0][:52]:<54} {f[13] + f[3] + f[4] + f[6] + f[14] + f[17]:.1f} g")
    print("dry run, nothing written" if args.dry_run else "written")
