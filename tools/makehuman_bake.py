#!/usr/bin/env python3
"""Bake data/body/body-{m,f}.glb from MakeHuman's CC0 mesh data.

Replaces the hand-built SDF placeholder (build_body_glb.py) with the
MakeHuman community's base mesh and macro targets — a professionally
sculpted body, so realism comes from their data rather than our tuning.

Inputs (all CC0, MakeHuman Team — www.makehumancommunity.org):
  base.obj                the hm08 base mesh, from
                          github.com/makehumancommunity/makehuman
                          (makehuman/data/3dobjs/base.obj)
  targets.npz             compiled morph targets, from the makehuman
                          pip wheel (makehuman/data/targets.npz);
                          int16 deltas at 1e-3 scale (see core/algos3d.py)
  default.mhskel          skeleton (makehuman/data/rigs/default.mhskel in the
                          same repo) — joint positions are the centroids of
                          the joint-* helper cubes in base.obj
  default_weights.mhw     per-bone vertex weights, JSON
                          (makehuman/data/rigs/default_weights.mhw)

What it does:
  1. Composes each fat level as base + caucasian-<sex>-young
     + weight-macro targets (minweight/averageweight/maxweight blended
     the way MakeHuman's macro slider does, muscle held at average).
  2. Lowers the arms from MakeHuman's 45° A-pose to a relaxed ~16°,
     by rotating each arm about its shoulder joint with the rotation
     angle scaled per-vertex by the arm bones' skin weights.
  3. Strips the helper geometry (targets index the full vertex list, so
     deltas are applied first; the body's vertices are 0..13379).
  4. Triangulates, faces +Z, metres, feet at y=0, base level scaled to
     exactly 1.75 m (the runtime scales by height/175).
  5. Writes through build_body_glb.write_glb — same contract, so the
     runtime does not change.

Usage: python3 tools/makehuman_bake.py <data-dir>
where <data-dir> holds mh_base.obj, targets.npz (or mhx/makehuman/data/
targets.npz), mh_default.mhskel, mh_default_weights.mhw.
"""
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_body_glb import LEVELS, vert_normals, write_glb  # noqa: E402

# Body-fat % → MakeHuman weight-macro position (0 = minweight,
# 0.5 = averageweight, 1 = maxweight; >1 extrapolates maxweight, which
# MakeHuman caps at merely chubby — nowhere near the top of our scale).
FAT_TO_W = {
    "m": {8: 0.18, 15: 0.32, 22: 0.46, 30: 0.66, 38: 0.92, 46: 1.30},
    "f": {12: 0.22, 18: 0.35, 25: 0.50, 32: 0.70, 40: 0.95, 48: 1.30},
}

# Detail targets layered on top over the upper half of the fat range —
# maxweight alone thickens evenly, obesity does not. Factors are the
# strength at the heaviest level; each ramps in with e = ((t-.5)/.5)^1.3
# where t is the level's position in [0,1].
FAT_KIT = {
    "f": [
        ("stomach/stomach-tone-decr", 0.60),
        ("stomach/stomach-pregnant-incr", 0.25),
        ("cheek/l-cheek-volume-incr", 0.55),
        ("cheek/r-cheek-volume-incr", 0.55),
        ("neck/neck-double-incr", 0.60),
        ("neck/neck-scale-horiz-incr", 0.35),
        ("hip/hip-scale-horiz-incr", 0.40),
        ("hip/hip-scale-depth-incr", 0.35),
        ("buttocks/buttocks-volume-incr", 0.45),
        ("torso/torso-scale-depth-incr", 0.35),
        ("armslegs/l-upperarm-fat-incr", 0.60),
        ("armslegs/r-upperarm-fat-incr", 0.60),
        ("armslegs/l-upperleg-fat-incr", 0.60),
        ("armslegs/r-upperleg-fat-incr", 0.60),
        ("armslegs/l-lowerarm-fat-incr", 0.35),
        ("armslegs/r-lowerarm-fat-incr", 0.35),
        ("armslegs/l-lowerleg-fat-incr", 0.35),
        ("armslegs/r-lowerleg-fat-incr", 0.35),
    ],
    "m": [
        ("stomach/stomach-tone-decr", 0.45),
        ("stomach/stomach-pregnant-incr", 0.50),
        ("cheek/l-cheek-volume-incr", 0.55),
        ("cheek/r-cheek-volume-incr", 0.55),
        ("neck/neck-double-incr", 0.70),
        ("neck/neck-scale-horiz-incr", 0.40),
        ("torso/torso-scale-depth-incr", 0.45),
        ("hip/hip-scale-depth-incr", 0.25),
        ("buttocks/buttocks-volume-incr", 0.20),
        ("armslegs/l-upperarm-fat-incr", 0.45),
        ("armslegs/r-upperarm-fat-incr", 0.45),
        ("armslegs/l-upperleg-fat-incr", 0.45),
        ("armslegs/r-upperleg-fat-incr", 0.45),
        ("armslegs/l-lowerarm-fat-incr", 0.30),
        ("armslegs/r-lowerarm-fat-incr", 0.30),
        ("armslegs/l-lowerleg-fat-incr", 0.30),
        ("armslegs/r-lowerleg-fat-incr", 0.30),
    ],
}
SEXNAME = {"m": "male", "f": "female"}
ARM_ANGLE = 16.0        # degrees from vertical the arms settle at
N_BODY = 13380          # body-group vertices are 0..N_BODY-1 in base.obj


def load_base(path):
    verts, faces, cur = [], [], None
    for line in open(path):
        if line.startswith("v "):
            verts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("g "):
            cur = line.split(None, 1)[1].strip()
        elif line.startswith("f ") and cur == "body":
            faces.append([int(p.split("/")[0]) - 1 for p in line.split()[1:]])
    return np.array(verts, dtype=np.float64), np.array(faces, dtype=np.int64)


class Targets:
    def __init__(self, npz_path):
        self.z = np.load(npz_path)

    def add(self, V, name, factor):
        """name is the path under targets/, e.g. 'macrodetails/caucasian-…'
        or 'stomach/stomach-tone-decr'."""
        idx = self.z["targets/%s.index" % name]
        vec = self.z["targets/%s.vector" % name].astype(np.float64)
        V[idx.astype(np.int64)] += vec * 1e-3 * factor


def weight_factors(w):
    """MakeHuman's weight-macro blend. w may exceed 1 (extrapolation)."""
    if w <= 0.5:
        return {"minweight": 1 - 2 * w, "averageweight": 2 * w}
    return {"averageweight": max(0.0, 2 - 2 * w), "maxweight": 2 * w - 1}


# Detail targets that give the muscle axis its visible bulk. The macro
# min/max-muscle grid mostly firms and softens — the shape that reads as
# "muscular" from across a room (pecs, lats, delts, thicker limbs, V-taper)
# lives in the detail library, exactly as the obesity shape did.
MUS_HI = [
    # Pectoral held well under the limbs: at full strength the pec mass
    # balloons and rides up toward the clavicle. Ab tone lives mostly on
    # the fat axis (LEAN_TONE) where it belongs — leanness reveals it —
    # so it is only seasoning here. The face rides along faintly: a
    # trained body carries a slightly cut face.
    ("torso/torso-muscle-pectoral-incr", 0.50),
    ("torso/torso-muscle-dorsi-incr", 1.00),
    ("torso/torso-vshape-incr", 0.80),
    ("stomach/stomach-tone-incr", 0.35),
    ("cheek/l-cheek-bones-incr", 0.25),
    ("cheek/r-cheek-bones-incr", 0.25),
    ("armslegs/l-upperarm-muscle-incr", 1.10),
    ("armslegs/r-upperarm-muscle-incr", 1.10),
    ("armslegs/l-upperarm-shoulder-muscle-incr", 1.05),
    ("armslegs/r-upperarm-shoulder-muscle-incr", 1.05),
    ("armslegs/l-lowerarm-muscle-incr", 0.90),
    ("armslegs/r-lowerarm-muscle-incr", 0.90),
    ("armslegs/l-upperleg-muscle-incr", 1.00),
    ("armslegs/r-upperleg-muscle-incr", 1.00),
    ("armslegs/l-lowerleg-muscle-incr", 0.90),
    ("armslegs/r-lowerleg-muscle-incr", 0.90),
]
MUS_LO = [
    ("torso/torso-muscle-pectoral-decr", 0.45),
    ("torso/torso-muscle-dorsi-decr", 0.40),
    ("armslegs/l-upperarm-muscle-decr", 0.55),
    ("armslegs/r-upperarm-muscle-decr", 0.55),
    ("armslegs/l-lowerarm-muscle-decr", 0.40),
    ("armslegs/r-lowerarm-muscle-decr", 0.40),
    ("armslegs/l-upperleg-muscle-decr", 0.45),
    ("armslegs/r-upperleg-muscle-decr", 0.45),
    ("armslegs/l-lowerleg-muscle-decr", 0.40),
    ("armslegs/r-lowerleg-muscle-decr", 0.40),
]
# The third extra target: emaciated. The morph range used to bottom out at
# "slim" — 40 kg at 7% wore the same body as 60 kg. This is minweight pushed
# past MakeHuman's floor plus minmuscle, with the frame narrowed and the face
# hollowed, so an underweight body finally looks underweight.
THIN_KIT = [
    ("torso/torso-scale-horiz-decr", 0.40),
    ("neck/neck-scale-horiz-decr", 0.40),
    ("cheek/l-cheek-volume-decr", 0.90),
    ("cheek/r-cheek-volume-decr", 0.90),
    ("cheek/l-cheek-bones-incr", 0.45),
    ("cheek/r-cheek-bones-incr", 0.45),
    ("armslegs/l-upperarm-scale-horiz-decr", 0.35),
    ("armslegs/r-upperarm-scale-horiz-decr", 0.35),
    ("armslegs/l-upperleg-scale-horiz-decr", 0.30),
    ("armslegs/r-upperleg-scale-horiz-decr", 0.30),
]


def compose(base, targets, sex, bf, levels, muscle="averagemuscle", wov=None):
    t = (bf - levels[0]) / (levels[-1] - levels[0])
    V = base.copy()
    targets.add(V, "macrodetails/caucasian-%s-young" % SEXNAME[sex], 1.0)
    for name, f in weight_factors(
            FAT_TO_W[sex][bf] if wov is None else wov).items():
        if f:
            targets.add(V, "macrodetails/universal-%s-young-%s-%s"
                        % (SEXNAME[sex], muscle, name), f)
    e = max(0.0, (t - 0.5) / 0.5) ** 1.3
    if e > 0:
        for name, top in FAT_KIT[sex]:
            targets.add(V, name, top * e)
    # Definition is what leanness reveals: stomach tone and a leaner face ramp
    # in over the bottom third of the fat range, so the body sharpens as the
    # slider drops rather than only when FFMI is high.
    lean = max(0.0, (0.35 - t) / 0.35)
    if lean > 0:
        targets.add(V, "stomach/stomach-tone-incr",
                    (0.75 if sex == "m" else 0.50) * lean)
        targets.add(V, "cheek/l-cheek-volume-decr", 0.30 * lean)
        targets.add(V, "cheek/r-cheek-volume-decr", 0.30 * lean)
    if muscle != "averagemuscle":
        for name, f in (MUS_HI if muscle == "maxmuscle" else MUS_LO):
            targets.add(V, name, f)
    return V


def arm_blend(weights_path):
    """Per-vertex share of arm-bone skin weight, per side."""
    wt = json.load(open(weights_path))["weights"]
    pat = re.compile(r"^(upperarm|lowerarm|wrist|metacarpal|finger)")
    out = {}
    for side in "LR":
        w = np.zeros(19158)
        for bone, pairs in wt.items():
            if pat.match(bone) and bone.endswith("." + side):
                for vi, ww in pairs:
                    w[vi] += ww
        out[side] = np.clip(w, 0.0, 1.0)
    return out


def rodrigues(axis, ang):
    x, y, z = axis
    c, s = np.cos(ang), np.sin(ang)
    C = 1 - c
    return np.array([
        [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
        [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
        [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def lower_arms(V, joints, blend):
    """Rotate each arm about its shoulder head so it hangs at ARM_ANGLE
    from vertical, angle scaled per-vertex by the arm skin weight."""
    out = V.copy()
    for side, sgn in (("L", 1.0), ("R", -1.0)):
        pivot = V[joints["upperarm01.%s____head" % side]].mean(axis=0)
        tip = V[joints["wrist.%s____head" % side]].mean(axis=0)
        s = tip - pivot
        d = np.array([sgn * np.sin(np.radians(ARM_ANGLE)),
                      -np.cos(np.radians(ARM_ANGLE)), 0.0])
        s_u = s / np.linalg.norm(s)
        axis = np.cross(s_u, d)
        na = np.linalg.norm(axis)
        if na < 1e-9:
            continue
        axis /= na
        theta = np.arccos(np.clip(np.dot(s_u, d), -1, 1))
        w = blend[side]
        moved = np.nonzero(w > 1e-4)[0]
        for vi in moved:
            R = rodrigues(axis, theta * w[vi])
            out[vi] = pivot + R @ (V[vi] - pivot)
    return out


def build(sex, data_dir, base, faces, targets, joints, blend, out_dir):
    levels = LEVELS[sex]
    posed = []
    for bf in levels:
        V = compose(base, targets, sex, bf, levels)
        posed.append(lower_arms(V, joints, blend))

    # Muscle, as its own axis. Fat levels are baked at average muscle; these
    # two deltas — MakeHuman's min/max-muscle grid against the average, at
    # the mid fat level — let the runtime add or strip lean mass on top of
    # any fat level, driven by FFMI. Additive rather than the full 2D grid,
    # which is a close approximation at a fraction of the bytes.
    REF = 2
    posed_mus = [lower_arms(compose(base, targets, sex, levels[REF], levels,
                                    muscle=mus), joints, blend)
                 for mus in ("minmuscle", "maxmuscle")]

    # helper geometry off; body verts are the first N_BODY
    tris = []
    for q in faces:
        tris.append([q[0], q[1], q[2]])
        tris.append([q[0], q[2], q[3]])
    tris = np.array(tris, dtype=np.int64)
    bodies = [P[:N_BODY] for P in posed]

    # orient/scale: MakeHuman is Y-up, faces +Z, decimetres. One transform,
    # taken from the leanest level, applied to every level.
    b0 = bodies[0]
    ymin, ymax = b0[:, 1].min(), b0[:, 1].max()
    scale = 1.75 / ((ymax - ymin) * 0.1)
    zc = b0[:, 2].mean() * 0.1 * scale

    def xf(P):
        M = P * 0.1 * scale
        M[:, 1] -= ymin * 0.1 * scale
        M[:, 2] -= zc
        return np.ascontiguousarray(M)

    out = [xf(P) for P in bodies]
    base_v = out[0]
    base_n = vert_normals(base_v, tris)
    tgts = [(v, vert_normals(v, tris)) for v in out[1:]]
    muscle = []
    for P in posed_mus:
        v = base_v + (xf(P[:N_BODY]) - out[REF])
        muscle.append((v, vert_normals(v, tris)))
    # The emaciated target, measured against the leanest level it stacks on.
    Vt = compose(base, targets, sex, levels[0], levels,
                 muscle="minmuscle", wov=-0.1)
    for name, f in THIN_KIT:
        targets.add(Vt, name, f)
    v = base_v + (xf(lower_arms(Vt, joints, blend)[:N_BODY]) - out[0])
    muscle.append((v, vert_normals(v, tris)))
    path = os.path.join(out_dir, "body-%s.glb" % sex)
    total = write_glb(path, sex, base_v, base_n, tris, tgts, levels,
                      muscle=muscle)
    print("%s: %d verts, %d tris, %d fat levels + 3 extras, %.2f MB -> %s"
          % (sex, len(base_v), len(tris), len(levels), total / 1e6, path))


def main():
    data_dir = sys.argv[1]
    npz = os.path.join(data_dir, "targets.npz")
    if not os.path.exists(npz):
        npz = os.path.join(data_dir, "mhx/makehuman/data/targets.npz")
    base, faces = load_base(os.path.join(data_dir, "mh_base.obj"))
    targets = Targets(npz)
    sk = json.load(open(os.path.join(data_dir, "mh_default.mhskel")))
    joints = sk["joints"]
    blend = arm_blend(os.path.join(data_dir, "mh_default_weights.mhw"))
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "data", "body")
    for sex in ("f", "m"):
        build(sex, data_dir, base, faces, targets, joints, blend, out_dir)


if __name__ == "__main__":
    main()
