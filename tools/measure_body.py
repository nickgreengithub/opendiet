#!/usr/bin/env python3
"""Measure the shipped body meshes the way a tape and a water tank would.

The figure is driven by arithmetic — fat-mass index sets the fat morph, FFMI
sets the muscle one — but nothing has ever checked that the shape those
weights produce is the size the numbers claim. This does.

Two kinds of check:

  Volume.  A body of a known mass and a known fat fraction has a known
  volume: fat is 0.9007 kg/L and fat-free mass 1.1 kg/L (Siri 1961), so
  V = m_fat/0.9007 + m_lean/1.1, plus the air a scan sees and densitometry
  subtracts — residual lung volume and a little gut gas. The mesh's own
  volume is the divergence theorem over its triangles. If the two disagree
  by 10%, the figure is the wrong size for the numbers under it, and no
  amount of looking at it will say so.

  Girths.  Waist, chest, hip, thigh, arm and neck, each as the convex-hull
  perimeter of a horizontal slice — a tape bridges a hollow rather than
  falling into it, so the hull is the honest analogue. Slices are traced
  into closed loops first, because at chest height the plane cuts the arms
  as well, and at hip height the hands.

Reference girths (ANSUR II, public domain, 6,068 subjects) are not bundled:
drop the two public CSVs beside this script as ansur_ii_male.csv and
ansur_ii_female.csv and the report gains a measured column to argue with.

Usage:
  python3 tools/measure_body.py                 # the default grid
  python3 tools/measure_body.py --sex m --ht 175 --kg 84 --bf 24
"""
import argparse
import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = os.path.join(HERE, "..", "data", "body", "body-%s.glb")

# Siri's two compartments, and the air a 3D scan sees but hydrostatic
# weighing takes back out: residual lung volume plus gastrointestinal gas.
D_FAT, D_LEAN = 0.9007, 1.1
RESIDUAL_L = {"m": 1.2, "f": 1.0}
GUT_GAS_L = 0.1

# The runtime's own anchors, mirrored here rather than imported, because the
# point of this tool is to measure what the browser actually draws. Keep in
# step with body.js: FMI_LEVELS, the FFMI anchors and the two masks.
FMI_LEVELS = {"m": [1.9, 3.7, 5.9, 9.0, 13.2, 18.6],
              "f": [2.4, 3.8, 5.8, 8.2, 12.1, 17.3]}
FFMI_ANCHOR = {"m": {"lo": 15.5, "avg": 18.5, "hi": 22.5},
               "f": {"lo": 12.5, "avg": 15.0, "hi": 18.5}}


def read_glb(path):
    """POSITION, indices and every morph target's POSITION delta, plus the
    extras block that names them."""
    raw = open(path, "rb").read()
    magic, _, _ = struct.unpack_from("<III", raw, 0)
    assert magic == 0x46546C67, "not a glb"
    off, js, bin_ = 12, None, None
    while off < len(raw):
        ln, kind = struct.unpack_from("<II", raw, off)
        data = raw[off + 8:off + 8 + ln]
        if kind == 0x4E4F534A:
            js = json.loads(data.decode("utf-8"))
        elif kind == 0x004E4942:
            bin_ = data
        off += 8 + ln
    prim = js["meshes"][0]["primitives"][0]

    def acc(i):
        a = js["accessors"][i]
        bv = js["bufferViews"][a["bufferView"]]
        n = a["count"] * {"VEC3": 3, "SCALAR": 1}[a["type"]]
        dt = {5126: "<f4", 5125: "<u4"}[a["componentType"]]
        arr = np.frombuffer(bin_, dtype=dt, count=n,
                            offset=bv.get("byteOffset", 0))
        return arr.reshape(a["count"], -1).astype(np.float64)

    base = acc(prim["attributes"]["POSITION"])
    tris = acc(prim["indices"]).astype(np.int64).reshape(-1, 3)
    deltas = [acc(t["POSITION"]) for t in prim["targets"]]
    return base, tris, deltas, js["meshes"][0].get("extras", {})


def hat_weights(levels, v):
    """body.js weightsFor: one parameter across N shapes is a hat function,
    so the result is exactly the interpolation of the two shapes either
    side."""
    w = [0.0] * (len(levels) - 1)
    v = max(levels[0], min(levels[-1], v))
    for i in range(len(levels) - 1):
        a, b = levels[i], levels[i + 1]
        if a <= v <= b:
            t = (v - a) / (b - a)
            if i > 0:
                w[i - 1] = 1 - t
            w[i] = t
            break
    return w


def blend(base, deltas, sex, ht, kg, bf):
    """The runtime's applyTo, in numpy: fat morphs off fat-mass index, the
    muscle pair off FFMI with the two masks, then the height scale."""
    hm = (ht / 100.0) ** 2
    n_fat = len(FMI_LEVELS[sex]) - 1
    w = hat_weights(FMI_LEVELS[sex], kg * (bf / 100.0) / hm) + [0.0] * 3
    ffmi = kg * (1 - bf / 100.0) / hm
    A = FFMI_ANCHOR[sex]
    mask = max(0.35, min(1.0, 1.35 - 0.03 * bf))
    lo_mask = max(0.25, min(1.0, 0.2 + (bf - 10) / 25.0))
    if ffmi >= A["avg"]:
        m = min(1.3, (ffmi - A["avg"]) / (A["hi"] - A["avg"])) * mask
    else:
        m = -min(1.0, (A["avg"] - ffmi) / (A["avg"] - A["lo"])) * lo_mask
    thin = max(0.0, min(1.2, (A["lo"] - ffmi) / 3.5))
    w[n_fat] = (-m if m < 0 else 0.0) * (1 - min(1.0, thin))
    w[n_fat + 1] = m if m > 0 else 0.0
    w[n_fat + 2] = thin
    V = base.copy()
    for i, wi in enumerate(w):
        if wi:
            V += wi * deltas[i]
    return V * (ht / 175.0), ffmi


def volume_l(V, tris):
    """Signed volume by the divergence theorem, in litres."""
    a, b, c = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    return abs(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0) * 1000.0


def open_edges(tris):
    """How watertight the mesh is: edges owned by one triangle only."""
    e = np.vstack([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    e = np.sort(e, axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return int((counts == 1).sum())


def loops_at(V, tris, y):
    """Slice at height y and trace the closed contours. Returns a list of
    (points Nx2 in x/z, centroid x). Tracing matters: at chest height the
    plane cuts both arms as well as the ribs."""
    a, b, c = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    ya, yb, yc = a[:, 1], b[:, 1], c[:, 1]
    lo = np.minimum(np.minimum(ya, yb), yc)
    hi = np.maximum(np.maximum(ya, yb), yc)
    hit = (lo <= y) & (hi >= y)
    if not hit.any():
        return []
    a, b, c = a[hit], b[hit], c[hit]
    segs = []
    for p, q in ((a, b), (b, c), (c, a)):
        yp, yq = p[:, 1], q[:, 1]
        cross = ((yp - y) * (yq - y) <= 0) & (yp != yq)
        if not cross.any():
            segs.append(None)
            continue
        t = ((y - yp[cross]) / (yq[cross] - yp[cross]))[:, None]
        segs.append((np.where(cross)[0], p[cross] + t * (q[cross] - p[cross])))
    pts, owner = [], []
    for s in segs:
        if s is None:
            continue
        idx, xyz = s
        pts.append(xyz)
        owner.append(idx)
    if not pts:
        return []
    pts = np.vstack(pts)
    owner = np.concatenate(owner)
    # Two crossings per cut triangle; join them into loops with union-find on
    # the rounded intersection points, which are identical across the shared
    # edge of two neighbouring triangles.
    key = np.round(pts * 1e6).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True,
                              return_inverse=True)
    parent = list(range(len(first)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    order = np.argsort(owner, kind="stable")
    o_sorted, inv_sorted = owner[order], inv[order]
    starts = np.searchsorted(o_sorted, np.unique(o_sorted))
    ends = np.append(starts[1:], len(o_sorted))
    for st, en in zip(starts, ends):
        for k in range(st + 1, en):
            union(inv_sorted[st], inv_sorted[k])
    roots = {}
    for i in range(len(first)):
        roots.setdefault(find(i), []).append(i)
    out = []
    upts = pts[first]
    for _, members in roots.items():
        P = upts[members][:, [0, 2]]
        if len(P) >= 6:
            out.append((P, float(P[:, 0].mean())))
    return out


def hull_perimeter(P):
    """Monotone chain hull, perimeter in centimetres — a tape bridges a
    hollow rather than falling into it."""
    pts = np.unique(np.round(P, 6), axis=0)
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    if len(pts) < 3:
        return 0.0

    def half(ps):
        st = []
        for p in ps:
            while len(st) >= 2:
                (x1, y1), (x2, y2) = st[-2], st[-1]
                if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) > 0:
                    break
                st.pop()
            st.append(tuple(p))
        return st

    h = half(pts)[:-1] + half(pts[::-1])[:-1]
    h = np.array(h)
    d = np.roll(h, -1, axis=0) - h
    return float(np.hypot(d[:, 0], d[:, 1]).sum() * 100.0)


# A closed mesh carries more than its outline: eyeballs are their own shells,
# so any loop too small to be a body part is thrown away before the nearest
# one to the axis is taken for the torso.
MIN_LOOP_CM = 15.0


def torso_girth(V, tris, y):
    ls = [(P, cx) for (P, cx) in loops_at(V, tris, y)
          if hull_perimeter(P) >= MIN_LOOP_CM]
    if not ls:
        return 0.0
    P, _ = min(ls, key=lambda t: abs(t[1]))
    return hull_perimeter(P)


def limb_girth(V, tris, y, near_axis):
    """The larger of the two side loops — an arm or a thigh, not the torso."""
    ls = [(P, cx) for (P, cx) in loops_at(V, tris, y)
          if abs(cx) > near_axis and hull_perimeter(P) >= MIN_LOOP_CM]
    if len(ls) < 2:
        return 0.0
    return max(hull_perimeter(P) for P, _ in ls)


# Landmarks as fractions of stature, standing: the bands each measurement is
# hunted in, and whether the tape wants the narrowest or the widest slice in
# it. Nipple line at .72, natural waist at .62, buttock at .51, gluteal
# furrow at .45, mid-humerus at .71 with the arm hanging.
BANDS = {
    "neck": (torso_girth, .845, .875, min, {}),
    "chest": (torso_girth, .700, .745, max, {}),
    "waist": (torso_girth, .575, .665, min, {}),
    "hip": (torso_girth, .470, .545, max, {}),
    "thigh": (limb_girth, .415, .460, max, {"near_axis": 0.03}),
    "arm": (limb_girth, .680, .745, max, {"near_axis": 0.13}),
}


def measure(V, tris, sex, at=False):
    top = V[:, 1].max()
    out = {}
    for name, (f, lo, hi, pick, kw) in BANDS.items():
        ys = np.linspace(lo * top, hi * top, 26)
        vals = [(f(V, tris, y, **kw), y) for y in ys]
        vals = [v for v in vals if v[0] >= MIN_LOOP_CM]
        g, y = pick(vals) if vals else (0.0, 0.0)
        out[name] = g
        if at:
            out[name + "@"] = y / top
    return out


def implied_volume_l(sex, kg, bf):
    fat = kg * bf / 100.0
    return (fat / D_FAT + (kg - fat) / D_LEAN
            + RESIDUAL_L[sex] + GUT_GAS_L)


def row(sex, ht, kg, bf, cache={}):
    if sex not in cache:
        cache[sex] = read_glb(GLB % sex)
    base, tris, deltas, _ = cache[sex]
    V, ffmi = blend(base, deltas, sex, ht, kg, bf)
    vol = volume_l(V, tris)
    want = implied_volume_l(sex, kg, bf)
    g = measure(V, tris, sex)
    hm = (ht / 100.0) ** 2
    return {"sex": sex, "ht": ht, "kg": kg, "bf": bf,
            "bmi": kg / hm, "fmi": kg * bf / 100.0 / hm, "ffmi": ffmi,
            "vol": vol, "want": want, "err": 100 * (vol - want) / want,
            "mesh_kg": vol_to_kg(vol, sex, bf),
            # What a girth-only correction would cost: widening x and z by k
            # multiplies volume by k squared, so this is the scale that would
            # put the figure on its own arithmetic without touching height.
            "k": (want / vol) ** 0.5, **g}


def vol_to_kg(vol_l, sex, bf):
    """What the mesh would weigh at the stated fat fraction — the volume
    check, read as the number the user actually typed."""
    v = vol_l - RESIDUAL_L[sex] - GUT_GAS_L
    return v / ((bf / 100.0) / D_FAT + (1 - bf / 100.0) / D_LEAN)


def level_report(sex):
    """What each baked fat level actually IS. A level was sculpted as some
    reference body at its own body-fat percentage; its volume says what that
    body weighs. Run it against the fat-mass index the runtime anchors that
    level at, and the gap is the calibration error before a single slider
    moves."""
    base, tris, deltas, extras = read_glb(GLB % sex)
    levels = extras["bodyFat"]
    out = []
    for i, bf in enumerate(levels):
        V = base.copy()
        # Level i is every delta below it fully on — the deltas are measured
        # from the leanest shape, so leaving them out snaps back to it.
        for k in range(i):
            V += deltas[k]
        vol = volume_l(V, tris)
        kg = vol_to_kg(vol, sex, bf)
        fmi = kg * bf / 100.0 / (1.75 ** 2)
        out.append((bf, vol, kg, fmi, FMI_LEVELS[sex][i]))
    return out


GRID = [
    ("m", 175, 60, 10), ("m", 175, 70, 15), ("m", 175, 84, 24),
    ("m", 175, 95, 30), ("m", 175, 110, 36), ("m", 190, 95, 20),
    ("m", 165, 70, 25), ("m", 175, 78, 12),
    ("f", 163, 50, 18), ("f", 163, 58, 25), ("f", 163, 68, 32),
    ("f", 163, 80, 40), ("f", 178, 70, 26), ("f", 155, 60, 33),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sex")
    ap.add_argument("--ht", type=float)
    ap.add_argument("--kg", type=float)
    ap.add_argument("--bf", type=float)
    ap.add_argument("--levels", action="store_true",
                    help="what each baked fat level actually weighs")
    ap.add_argument("--measured-anchors", action="store_true",
                    help="re-run the grid with each level anchored at the "
                         "fat-mass index its shape actually has")
    a = ap.parse_args()
    if a.measured_anchors:
        for sex in ("m", "f"):
            FMI_LEVELS[sex] = [round(r[3], 1) for r in level_report(sex)]
            print("%s anchors -> %s" % (sex, FMI_LEVELS[sex]))
    if a.levels:
        for sex in ("m", "f"):
            print("\n%s — each baked level at 1.75 m, muscle neutral" % sex)
            print("  bf%   vol L   implies kg   its FMI   anchored at   off by")
            for bf, vol, kg, fmi, anc in level_report(sex):
                print("  %3d %7.1f %12.1f %9.1f %13.1f %8.1f"
                      % (bf, vol, kg, fmi, anc, fmi - anc))
        return
    grid = ([(a.sex, a.ht, a.kg, a.bf)]
            if a.sex and a.ht and a.kg and a.bf else GRID)
    for sex in ("m", "f"):
        base, tris, _, _ = read_glb(GLB % sex)
        print("%s: %d verts, %d tris, %d open edges"
              % (sex, len(base), len(tris), open_edges(tris)))
    head = ("sex  ht   kg   bf%  bmi  ffmi | mesh L  want L   err%  mesh kg"
            "     k | neck chest waist   hip thigh   arm")
    print("\n" + head)
    print("-" * len(head))
    for g in grid:
        r = row(*g)
        print("%-3s %4.0f %4.0f %4.0f %5.1f %5.1f | %6.1f %7.1f %6.1f %8.1f"
              " %5.3f | %4.0f %5.0f %5.0f %5.0f %5.0f %5.0f"
              % (r["sex"], r["ht"], r["kg"], r["bf"], r["bmi"], r["ffmi"],
                 r["vol"], r["want"], r["err"], r["mesh_kg"], r["k"],
                 r["neck"], r["chest"], r["waist"], r["hip"],
                 r["thigh"], r["arm"]))


if __name__ == "__main__":
    main()
