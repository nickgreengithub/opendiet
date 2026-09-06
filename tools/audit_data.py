#!/usr/bin/env python3
"""Check a library for figures that are not figures.

A nutrient nobody analysed and a nutrient measured at zero used to arrive in these files
as the same 0 — see data/README.md. tools/build_data.py keeps the difference now, but a
file built before that cannot say which of its zeros are real, so this asks the numbers
instead. Every check here is a statement the food itself has to answer for:

  · energy is a known function of the macros, so a macro that is missing shows up as
    energy the stated macros cannot account for;
  · the parts of 100 g have to reach 100 g, so missing water shows up as a shortfall;
  · fat that is more than a gram is made of saturated, mono and poly fat, so a food with
    fat and no breakdown at all has a breakdown nobody measured;
  · and the parts of a figure cannot exceed it.

A contradiction is a fault and fails the run. A suspicion — the fibre and sugar zeros —
is only counted: half the entries carry a zero there and the numbers cannot say which of
them nobody measured. Only the source can, which is why the fix is in the build.

    python3 tools/audit_data.py                # every library in data/
    python3 tools/audit_data.py --lib legacy   # one of them
    python3 tools/audit_data.py --show 20      # more of each fault
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

IX = {"name": 0, "cat": 1, "kcal": 2, "p": 3, "c": 4, "fb": 5, "f": 6, "sf": 7, "sg": 8,
      "ml": 9, "cm": 10, "pg": 11, "pn": 12, "wa": 13, "ah": 14, "mo": 15, "po": 16,
      "al": 17, "tr": 18}
# Energy per gram, near enough. The specific factors USDA uses per food run a few per cent
# either way, which is why a contradiction has to be a share of the energy as well as an
# amount of the macro.
ATWATER = {"p": 4, "c": 4, "f": 9, "al": 7}
SLACK = 0.12       # energy the general factors may miss before it means anything
MIN_GRAMS = 2.0    # and an amount below this is rounding, not a missing measurement
# Organic acids carry energy no macro accounts for — vinegar is 18 kcal of acetic acid and
# nothing else — so a small shortfall is the model's, not the food's.
MIN_KCAL = 25
# Carbohydrate is what is left when everything else is weighed, so its parts, which are
# weighed, can come to slightly more than it. Only a real overshoot is a fault.
PART_SLACK, PART_GRAMS = 0.05, 1.0


def get(row, k):
    i = IX[k]
    v = row[i] if i < len(row) else 0
    return 0 if v is None else v


def energy(row):
    return sum(f * get(row, k) for k, f in ATWATER.items())


def check(foods):
    """Returns [(fault, [(line, name), ...]), ...] and a dict of counted suspicions."""
    faults = []

    for macro, per in (("p", 4), ("c", 4), ("f", 9)):
        hits = []
        for r in foods:
            if get(r, macro) != 0:
                continue
            gap = get(r, "kcal") - energy(r)
            if (gap / per > MIN_GRAMS and gap > MIN_KCAL
                    and gap > SLACK * get(r, "kcal")):
                hits.append((f"{gap / per:5.1f} g of it is missing from "
                             f"{get(r, 'kcal'):.0f} kcal", r[IX["name"]]))
        if hits:
            faults.append((f"{macro} is zero and the energy says otherwise", hits))

    hits = []
    for r in foods:
        if get(r, "wa") != 0:
            continue
        parts = sum(get(r, k) for k in ("p", "c", "f", "ah", "al"))
        if parts < 90:
            hits.append((f"{100 - parts:5.1f} g of the 100 unaccounted for", r[IX["name"]]))
    if hits:
        faults.append(("water is zero and the parts do not reach 100 g", hits))

    hits = []
    for r in foods:
        fat = get(r, "f")
        if fat > 1 and sum(get(r, k) for k in ("sf", "mo", "po", "tr")) == 0:
            hits.append((f"{fat:5.1f} g of fat broken into nothing", r[IX["name"]]))
    if hits:
        faults.append(("fat with no breakdown at all", hits))

    for whole, parts, name in (("f", ("sf", "mo", "po", "tr"), "fat"),
                               ("c", ("fb", "sg"), "carbohydrate")):
        hits = []
        for r in foods:
            got, whole_v = sum(get(r, k) for k in parts), get(r, whole)
            if got - whole_v > max(PART_GRAMS, PART_SLACK * whole_v):
                hits.append((f"{got:5.1f} g of parts to {whole_v:.1f} g of {name}",
                             r[IX["name"]]))
        if hits:
            faults.append((f"the parts come to more than the {name}", hits))

    suspect = {}
    for sub, parent in (("sg", "c"), ("fb", "c"), ("sf", "f"), ("mo", "f"), ("po", "f")):
        suspect[sub] = sum(1 for r in foods
                           if get(r, sub) == 0 and get(r, parent) > 0.5)
    return faults, suspect


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lib", action="append", help="a library to check; repeatable")
    ap.add_argument("--show", type=int, default=6, help="lines to print per fault")
    args = ap.parse_args()
    libs = args.lib or sorted(p.stem for p in (ROOT / "data").glob("*.json"))

    total = 0
    for lib in libs:
        d = json.loads((ROOT / "data" / f"{lib}.json").read_text())
        foods = d["foods"]
        faults, suspect = check(foods)
        measured = d.get("zeros") == "measured"
        promise = "every zero measured" if measured else "cannot say which zeros are real"
        print(f"{lib}: {len(foods)} foods, {promise}")
        for fault, hits in faults:
            total += len(hits)
            print(f"  {len(hits):5}  {fault}")
            for line, name in hits[:args.show]:
                print(f"           {line}   {name[:58]}")
            if len(hits) > args.show:
                print(f"           … {len(hits) - args.show} more")
        if not measured:
            worst = ", ".join(f"{k} {v}" for k, v in suspect.items() if v)
            print(f"  {'':5}  zeros under a parent that is not zero, which the numbers "
                  f"cannot rule on: {worst}")
        print()
    if total:
        print(f"{total} contradicted figures", file=sys.stderr)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
