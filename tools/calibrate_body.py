#!/usr/bin/env python3
"""Fit the bake's fat constants to ANSUR II.

The figure's shape used to be argued about. This settles it: bake a
candidate, measure its girths the way a tape would, compare against the
soldiers who share that stature, weight and body fat, and keep what lands
closest. The bake is under two seconds, so a coordinate descent over the
handful of constants that matter converges in minutes.

Seven knobs per sex, each one a thing you could point at on the body:

  wmac    how hard the weight macro is pushed at the upper three levels
  belly   stomach/stomach-pregnant-incr — the abdomen itself
  tone    stomach/stomach-tone-decr — the slack over it
  torso   torso/torso-scale-depth-incr — the ribcage front to back
  twide   torso/torso-scale-horiz-incr — the ribcage side to side
  hips    hip scale and buttock volume together
  arms    the two arm fat targets
  legs    the two leg fat targets
  ramp0   where in the fat range the detail kit starts at all
  ramp    the exponent it rises with — a flat ramp buys mid-range mass
          without inflating the top level into a body nobody reaches

The anchors the runtime blends on are not fitted: after every bake each
level is measured and anchored at the fat-mass index its shape actually
has, so shape and anchor can never drift apart.

  python3 tools/calibrate_body.py --sex m --passes 3
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_body as MB  # noqa: E402

MH = os.environ.get("MH_DATA", "")
PARAMS = os.path.join(HERE, "..", "data", "body", "fat_params.json")

# The bodies the fit is judged on: a spread of weight at each of two heights
# per sex, since the error grows with weight and that is what has to be
# closed. Body fat is what a tape reads on ANSUR subjects of that size, so
# the comparison is like for like.
GRID = {
    "m": [(175, 62, 12), (175, 70, 16), (175, 78, 20), (175, 84, 24),
          (175, 92, 28), (175, 102, 32), (185, 85, 20), (168, 75, 24)],
    "f": [(163, 52, 20), (163, 58, 25), (163, 65, 29), (163, 72, 33),
          (163, 82, 38), (172, 68, 27), (156, 62, 31)],
}
# The waist is what the model gets most wrong, so it carries the most weight
# in the loss; the arm is nearly right already and is there to keep the fit
# from stealing from it.
GIRTH_W = {"m": {"waist": 2.5, "hip": 1.2, "chest": 1.2, "thigh": 1.0,
                 "arm": 0.8},
           # The female chest is the bust here and the chest at ANSUR: not the
           # same measurement, so it is a hint rather than a target. Scored at
           # full weight it drags the fit into shrinking the ribcage, which
           # takes the waist down with it.
           "f": {"waist": 2.5, "hip": 1.2, "chest": 0.3, "thigh": 1.0,
                 "arm": 0.8}}

BASE = {
    "belly": None, "tone": None, "torso": None,
    "hips": 1.0, "arms": 1.0, "legs": 1.0, "twide": 0.0,
    "ramp0": 0.5, "ramp": 1.3, "wmac": 1.0,
}
# Stage one is not fitted, it is solved. The six fat levels are one person
# gaining fat at constant lean mass — which is exactly what the runtime's two
# axes mean, fat on one and lean on the other — so level k is the body that
# weighs lean/(1-bf_k). Lean comes from the runtime's own average FFMI
# anchor, so shapes and anchors cannot disagree by construction. Letting an
# optimiser choose these instead buys mid-range accuracy by inflating the top
# level into a 360 kg body nobody will ever be blended to.
LEAN_FFMI = {"m": 18.5, "f": 15.0}


def level_targets(sex):
    import makehuman_bake as BK
    lean = LEAN_FFMI[sex] * 1.75 ** 2
    return [lean / (1 - b / 100.0) for b in sorted(BK.FAT_TO_W[sex])]
HIP_KEYS = ["hip/hip-scale-horiz-incr", "hip/hip-scale-depth-incr",
            "buttocks/buttocks-volume-incr"]
ARM_KEYS = ["armslegs/%s-%s-fat-incr" % (s, p) for s in ("l", "r")
            for p in ("upperarm", "lowerarm")]
LEG_KEYS = ["armslegs/%s-%s-fat-incr" % (s, p) for s in ("l", "r")
            for p in ("upperleg", "lowerleg")]


def defaults(sex, start=None):
    import makehuman_bake as BK
    kit = dict(BK.FAT_KIT[sex])
    p = dict(BASE)
    p["belly"] = kit["stomach/stomach-pregnant-incr"]
    p["tone"] = kit["stomach/stomach-tone-decr"]
    p["torso"] = kit["torso/torso-scale-depth-incr"]
    if start and os.path.exists(start):
        with open(start) as fh:
            saved = json.load(fh).get("_knobs", {}).get(sex)
        if saved:
            p.update(saved)
    return p


def to_json(sex, p, w=None):
    import makehuman_bake as BK
    if w is None:
        w = [BK.FAT_TO_W[sex][b] for b in sorted(BK.FAT_TO_W[sex])]
    # The macro is the blunt instrument — it thickens everything evenly — so
    # it is held on a short leash and only over the upper half, where the
    # detail kit alone cannot find enough mass. Fat goes to the abdomen
    # first, and the kit is what knows that.
    w = [v * (p.get("wmac", 1.0) if i >= 3 else 1.0)
         for i, v in enumerate(w)]
    kit = {"stomach/stomach-pregnant-incr": p["belly"],
           "stomach/stomach-tone-decr": p["tone"],
           "torso/torso-scale-depth-incr": p["torso"]}
    base = dict(BK.FAT_KIT[sex])
    for k in HIP_KEYS:
        if k in base:
            kit[k] = base[k] * p["hips"]
    for k in ARM_KEYS:
        if k in base:
            kit[k] = base[k] * p["arms"]
    for k in LEG_KEYS:
        if k in base:
            kit[k] = base[k] * p["legs"]
    kit["torso/torso-scale-horiz-incr"] = p["twide"]
    return {sex: {"w": w, "kit": kit, "ramp0": p["ramp0"],
                  "ramp": p["ramp"]}}


def bake(cfg):
    # Merge rather than overwrite: the file carries both sexes, and a run
    # fitting one of them must not clobber the other's numbers.
    out = {}
    if os.path.exists(PARAMS):
        with open(PARAMS) as fh:
            out = json.load(fh)
    out.update(cfg)
    with open(PARAMS, "w") as fh:
        json.dump(out, fh, indent=1)
    r = subprocess.run([sys.executable, os.path.join(HERE, "makehuman_bake.py"),
                        MH, PARAMS], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])


def loss(sex, verbose=False):
    """Rebuild the runtime anchors from the shapes just baked, then score the
    grid against ANSUR."""
    MB.read_glb.__defaults__ = None
    for d in (MB.row.__defaults__ or []):
        if isinstance(d, dict):
            d.clear()
    MB.FMI_LEVELS[sex] = [round(r[3], 2) for r in MB.level_report(sex)]
    # The six shapes have to sit where people are, not merely be correct
    # wherever they land: a level anchored at fat-mass index 77 is a shape the
    # blend can never reach, and spending it leaves four to cover everyone.
    # The ladder is one body gaining fat at constant lean, in index terms.
    lad = [t * b / 100.0 / 1.75 ** 2 for t, b in
           zip(level_targets(sex), sorted(__import__("makehuman_bake")
                                          .FAT_TO_W[sex]))]
    stretch = float(np.mean([(f - t) ** 2
                             for f, t in zip(MB.FMI_LEVELS[sex], lad)]))
    tot, rows = 0.0, []
    for ht, kg, bf in GRID[sex]:
        r = MB.row(sex, ht, kg, bf)
        ref, n = MB.ansur_near(sex, ht, kg, bf)
        if not ref:
            continue
        gw = GIRTH_W[sex]
        e = sum(gw[k] * (r[k] - ref[k]) ** 2 for k in gw)
        tot += e
        rows.append((ht, kg, bf, r, ref, n))
    if verbose:
        for ht, kg, bf, r, ref, n in rows:
            print("   %3d %3d %3d | " % (ht, kg, bf) + "  ".join(
                "%s %4.0f/%-4.0f" % (k, r[k], ref[k]) for k in GIRTH_W[sex])
                + " | vol %+5.1f%% n=%d" % (r["err"], n))
    if verbose:
        print("   ladder %s  (want %s)"
              % (" ".join("%.1f" % f for f in MB.FMI_LEVELS[sex]),
                 " ".join("%.1f" % t for t in lad)))
    return tot / max(1, len(rows)) + LADDER_W * stretch


# Girth error is in square centimetres and lands near 40 on a good fit. The
# ladder term is squared index units and runs into the hundreds when a level
# escapes, so this weight makes it a tiebreak between equally accurate fits
# rather than a goal in itself. At 1.0 it simply wins, and the fit trades
# fifteen centimetres of waist for a tidier ladder — which is the wrong
# trade: an unreachable level costs resolution, a wrong waist costs the
# truth.
LADDER_W = 0.05


W_FIT = {}


def evaluate(sex, p, verbose=False):
    bake(to_json(sex, p, W_FIT.get(sex)))
    return loss(sex, verbose)


def solve_weights(sex, p, rounds=9):
    """Drive each level's weight macro until that level's shape weighs what a
    body of its fat fraction and this lean mass has to weigh. Damped, because
    the macro is not linear in mass and the detail kit rides on top of it."""
    import makehuman_bake as BK
    w = [BK.FAT_TO_W[sex][b] for b in sorted(BK.FAT_TO_W[sex])]
    want = level_targets(sex)
    for i in range(rounds):
        bake(to_json(sex, p, w))
        got = [r[2] for r in MB.level_report(sex)]
        err = max(abs(g - t) / t for g, t in zip(got, want))
        print("  weights round %d, worst level off by %4.1f%%  (%s)"
              % (i, 100 * err, " ".join("%.0f" % g for g in got)))
        if err < 0.01:
            break
        w = [max(0.05, wk * (t / g) ** 0.55)
             for wk, g, t in zip(w, got, want)]
    W_FIT[sex] = w
    return w


STEPS = {"wmac": [0.06, 0.025], "belly": [0.25, 0.08],
         "tone": [0.2, 0.07], "torso": [0.2, 0.07], "twide": [0.2, 0.07],
         "hips": [0.2, 0.07], "arms": [0.2, 0.07], "legs": [0.2, 0.07],
         "ramp0": [0.08, 0.03], "ramp": [0.15, 0.06]}
# The bounds are not just numerical safety, they are the anatomy the tape
# cannot see. Left free, the fit finds the cheapest way to a correct waist —
# inflate one spherical belly target and starve the limbs, since a tape round
# the arm is only one number against several round the trunk. The result
# measures right and reads as a pregnancy on a thin man. So the abdomen
# target is capped, the trunk's own depth and width are allowed to do more of
# the work, and the limbs have a floor: a heavy body is heavy everywhere.
BOUNDS = {"wmac": (1.0, 2.3), "belly": (0.0, 1.6), "tone": (0.2, 2.0),
          "torso": (0.0, 2.5), "twide": (0.0, 2.2), "hips": (0.5, 2.5),
          "arms": (0.9, 2.5), "legs": (0.9, 2.5), "ramp0": (0.0, 0.6),
          "ramp": (0.35, 1.8)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sex", default="m")
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--start", action="store_true",
                    help="begin from the knobs already in fat_params.json")
    ap.add_argument("--ladder", action="store_true",
                    help="also solve each level's weight macro against the "
                         "constant-lean mass ladder")
    a = ap.parse_args()
    if not MH:
        raise SystemExit("set MH_DATA to the MakeHuman data directory")
    sex = a.sex
    p = defaults(sex, PARAMS if a.start else None)
    print("stage one: the levels as one body gaining fat at constant lean")
    print("  target kg: %s"
          % " ".join("%.0f" % t for t in level_targets(sex)))
    if a.ladder:
        solve_weights(sex, p)
    best = evaluate(sex, p, verbose=True)
    print("start loss %.1f  %s" % (best, p))
    n = 0
    for rnd in range(a.passes):
        for key in ("belly", "torso", "twide", "ramp", "ramp0", "hips",
                    "legs", "arms", "tone", "wmac"):
            step = STEPS[key][min(rnd, len(STEPS[key]) - 1)]
            improved = True
            while improved:
                improved = False
                for d in (step, -step):
                    q = dict(p)
                    lo, hi = BOUNDS[key]
                    q[key] = max(lo, min(hi, q[key] + d))
                    if q[key] == p[key]:
                        continue
                    v = evaluate(sex, q)
                    n += 1
                    if v < best - 1e-6:
                        best, p, improved = v, q, True
                        print("  %-6s %5.2f -> loss %7.1f" % (key, q[key], v))
                        break
    print("\n%d bakes, loss %.1f -> " % (n, best))
    print(json.dumps(p, indent=1))
    evaluate(sex, p, verbose=True)
    MB.FMI_LEVELS[sex] = [round(r[3], 2) for r in MB.level_report(sex)]
    print("\nbody.js FMI_LEVELS.%s = %s" % (sex, MB.FMI_LEVELS[sex]))
    # The knobs ride along in the file so a later run can pick up where this
    # one stopped; the bake ignores keys it does not know.
    out = to_json(sex, p, W_FIT.get(sex))
    if os.path.exists(PARAMS):
        with open(PARAMS) as fh:
            prev = json.load(fh)
        prev.update(out)
        out = prev
    out.setdefault("_knobs", {})[sex] = p
    out.setdefault("_anchors", {})[sex] = MB.FMI_LEVELS[sex]
    with open(PARAMS, "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
