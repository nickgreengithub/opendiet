#!/usr/bin/env python3
"""Check the FULLNESS weights against the only measured satiety data there is.

Holt SH, Brand Miller JC, Petocz P, Farmakalidis E. "A satiety index of common foods."
Eur J Clin Nutr 1995;49(9):675-90. Thirty-eight foods, served in equal 1000 kJ portions,
satiety rated every 15 minutes for two hours, scored against white bread = 100.

The weights in index.html were chosen by judgement. This asks what the evidence says about
them. It reports rank correlation, because ordering a table is what the column does, and it
judges every candidate leave-one-out: fit on 32 foods, predict the 33rd, correlate the
predictions no food helped to make. That distinction is the whole point — refitting all six
parameters scores better on the foods it was fitted to and much worse on a food it has not
seen, which is overfitting rather than calibration.

    python3 tools/calibrate_fullness.py

Needs numpy, and data/legacy.json.
"""
import itertools
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LIB = {a[0]: a for a in json.loads((ROOT / "data" / "legacy.json").read_text())["foods"]}

# Holt's food -> the SR Legacy entry that stands for it. Five of the 38 are branded cereals
# with no faithful generic in SR Legacy — All-Bran, Special K, Honey Smacks, Sustain, muesli
# — and are left out rather than matched to something they are not.
HOLT = [
    ("Potatoes, boiled", 323, "Potatoes, boiled, cooked without skin, flesh, without salt"),
    ("Ling fish", 225, "Fish, ling, cooked, dry heat"),
    ("Porridge", 209, "Cereals, oats, regular and quick, unenriched, cooked with water (includes boiling and microwaving), without salt"),
    ("Oranges", 202, "Oranges, raw, all commercial varieties"),
    ("Apples", 197, "Apples, raw, with skin"),
    ("Wholemeal pasta", 188, "Pasta, whole-wheat, cooked"),
    ("Beef", 176, 'Beef, round, eye of round roast, boneless, separable lean only, trimmed to 0" fat, select, cooked, roasted'),
    ("Baked beans", 168, "Beans, baked, canned, plain or vegetarian"),
    ("Grapes", 162, "Grapes, red or green (European type, such as Thompson seedless), raw"),
    ("Wholemeal bread", 157, "Bread, whole-wheat, commercially prepared"),
    ("Grain bread", 154, "Bread, multi-grain"),
    ("Popcorn", 154, "Snacks, popcorn, air-popped"),
    ("Eggs", 150, "Egg, whole, cooked, hard-boiled"),
    ("Cheese", 146, "Cheese, cheddar"),
    ("White rice", 138, "Rice, white, long-grain, regular, cooked, enriched, with salt"),
    ("Lentils", 133, "Lentils, mature seeds, cooked, boiled, without salt"),
    ("Brown rice", 132, "Rice, brown, long-grain, cooked"),
    ("Crackers", 127, "Crackers, standard snack-type, regular"),
    ("Cookies", 120, "Cookies, chocolate chip, commercially prepared, regular, lower fat"),
    ("White pasta", 119, "Pasta, cooked, enriched, without added salt"),
    ("Bananas", 118, "Bananas, raw"),
    ("Jellybeans", 118, "Candies, jellybeans"),
    ("Cornflakes", 118, "Cereals ready-to-eat, RALSTON Corn Flakes"),
    ("French fries", 116, "Potatoes, french fried, all types, salt added in processing, frozen, home-prepared, oven heated"),
    ("White bread", 100, "Bread, white, commercially prepared"),
    ("Ice cream", 96, "Ice creams, vanilla"),
    ("Crisps", 91, "Snacks, potato chips, plain, salted"),
    ("Yogurt", 88, "Yogurt, fruit, low fat, 10 grams protein per 8 ounce"),
    ("Peanuts", 84, "Peanuts, all types, dry-roasted, with salt"),
    ("Mars bar", 70, "Candies, MARS SNACKFOOD US, MILKY WAY Bar"),
    ("Doughnuts", 68, "Doughnuts, cake-type, plain"),
    ("Cake", 65, "Cake, sponge, commercially prepared"),
    ("Croissant", 47, "Croissants, butter"),
]

# What index.html uses. The last of them is what this script put there.
W = {"protein": 70.0, "carb": 20.0, "fat": 5.0, "fibre": 2.6, "bulk": 30.0, "sugar": -0.5}
TAU = 120.0
KEYS = list(W)
# Coarse on purpose: a fine grid is how you overfit 33 points.
GRID = {
    "protein": np.arange(20, 121, 10.0), "carb": np.arange(0, 61, 5.0),
    "fat": np.arange(0, 41, 5.0), "fibre": np.arange(0, 12.1, 0.8),
    "bulk": np.arange(0, 121, 10.0), "sugar": np.arange(-4, 0.01, 0.1),
}


def terms(a):
    """The five per-calorie quantities the score is built from, for one food row."""
    kcal, p, c, fb, f, sg = (a[2] or 1), a[3], a[4], a[5], a[6], a[8]
    tot = p * 4 + c * 4 + f * 9 or 1
    return {
        "protein": p * 4 / tot, "carb": c * 4 / tot, "fat": f * 9 / tot,
        "fibre": fb / kcal * 100, "bulk": 1 - math.exp(-(10000.0 / kcal) / TAU),
        "sugar": sg / kcal * 100,
    }


def predict(weights, rows):
    return np.array([sum(weights[k] * terms(LIB[n])[k] for k in KEYS) for _, _, n in rows])


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    ra, rb = ra - ra.mean(), rb - rb.mean()
    return float(ra @ rb / math.sqrt((ra @ ra) * (rb @ rb)))


def fit(free, rows):
    """Best setting of the named weights on these rows; the others stay where they are."""
    y = np.array([si for _, si, _ in rows], dtype=float)
    best = (-2.0, dict(W))
    for combo in itertools.product(*[GRID[k] for k in free]):
        w = dict(W)
        w.update(zip(free, combo))
        s = spearman(y, predict(w, rows))
        if s > best[0]:
            best = (s, w)
    return best


def leave_one_out(free):
    held = [float(predict(fit(free, HOLT[:i] + HOLT[i + 1:])[1], [HOLT[i]])[0])
            for i in range(len(HOLT))]
    return spearman(np.array([si for _, si, _ in HOLT], dtype=float), np.array(held))


if __name__ == "__main__":
    missing = [n for _, _, n in HOLT if n not in LIB]
    if missing:
        raise SystemExit("not in data/legacy.json:\n  " + "\n  ".join(missing))
    y = np.array([si for _, si, _ in HOLT], dtype=float)

    print(f"{len(HOLT)} of Holt's 38 foods matched to SR Legacy\n")
    print("shipping weights: Spearman %.3f" % spearman(y, predict(W, HOLT)))
    no_sugar = dict(W, sugar=0.0)
    print("without the sugar term:           %.3f" % spearman(y, predict(no_sugar, HOLT)))

    print("\nrefitting, judged on a food it never saw:")
    print("  %-24s %8s %10s" % ("free weights", "LOO", "in-sample"))
    # Pairs at most. An exhaustive six-way search over this grid is both slow and beside the
    # point: coordinate ascent on all six reaches 0.795 in sample and 0.530 out of it.
    cands = [()] + [(k,) for k in KEYS] + [("sugar", "bulk"), ("protein", "bulk"),
                                           ("protein", "carb"), ("fibre", "bulk")]
    for free in cands:
        ins = spearman(y, predict(W, HOLT)) if not free else fit(free, HOLT)[0]
        loo = spearman(y, predict(W, HOLT)) if not free else leave_one_out(free)
        print("  %-24s %8.3f %10.3f" % ("(none)" if not free else "+".join(free), loo, ins))

    print("\nsugar weight, one parameter, so in-sample is out-of-sample:")
    for ws in (0, -0.25, -0.5, -0.75, -1.0, -1.5, -2.0):
        print("  %5s   %.3f" % (ws, spearman(y, predict(dict(W, sugar=ws), HOLT))))

    print("\n%-18s %6s %9s" % ("food", "Holt", "score"))
    pred = predict(W, HOLT)
    for i in sorted(range(len(HOLT)), key=lambda j: -y[j]):
        print("%-18s %6d %9.0f" % (HOLT[i][0], y[i], max(0, min(100, pred[i]))))
