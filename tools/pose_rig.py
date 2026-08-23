#!/usr/bin/env python3
"""Skeleton-driven pose targets for the MakeHuman bake.

The bake already borrows the default skeleton once, to lower the arms from
the A-pose. This module borrows the whole of it: forward kinematics over the
bone hierarchy in default.mhskel, linear-blend skinning with the weights in
default_weights.mhw, so a pose authored as a handful of joint rotations
becomes a full-mesh morph target. Rest frames are world-aligned — every
bone's local rotation is authored about the model axes (X across, Y up,
Z forward), composing parent-to-child down the chain.

Poses are dicts of bone -> list of (axis, degrees). The keyframes that ship
(sitting at a laptop, pushing up out of the chair, two walk phases, two run
phases) live here too, so the bake script stays a pipeline.
"""
import numpy as np


def _rot(axis, deg):
    t = np.radians(deg)
    c, s = np.cos(t), np.sin(t)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


class Rig:
    """FK + LBS over the mhskel hierarchy, joints measured on the mesh the
    poses will deform (level-0, arms already lowered), so pivots sit where
    the shipped body's joints actually are."""

    def __init__(self, skel, weights, V):
        self.bones = {}          # name -> (parent, head position)
        self.order = []          # parents before children
        js = skel["joints"]
        for name, b in skel["bones"].items():
            head = V[np.array(js[b["head"]], dtype=np.int64)].mean(axis=0)
            self.bones[name] = (b.get("parent"), head)
        seen = set()

        def visit(n):
            if n in seen:
                return
            p = self.bones[n][0]
            if p:
                visit(p)
            seen.add(n)
            self.order.append(n)
        for n in self.bones:
            visit(n)
        # Per-bone weights, normalised per vertex so the skinning is a true
        # partition of unity (the file's sums drift a few percent).
        n_v = len(V)
        tot = np.zeros(n_v)
        self.w = {}
        for bone, pairs in weights.items():
            if bone not in self.bones:
                continue
            idx = np.array([p[0] for p in pairs], dtype=np.int64)
            val = np.array([p[1] for p in pairs], dtype=np.float64)
            self.w[bone] = (idx, val)
            np.add.at(tot, idx, val)
        tot[tot < 1e-9] = 1.0
        for bone, (idx, val) in self.w.items():
            self.w[bone] = (idx, val / tot[idx])

    def pose(self, V, spec):
        """Apply spec {bone: [(axis, deg), ...]} to V and return the posed
        copy. Unrotated chains are skipped whole, so a pose touching a dozen
        bones costs a dozen bones."""
        locR = {}
        for bone, rots in spec.items():
            R = np.eye(3)
            for axis, deg in rots:
                R = R @ _rot(axis, deg)
            locR[bone] = R
        world = {}                     # bone -> (P posed head, W world rot)
        moved = {}
        for name in self.order:
            parent, h = self.bones[name]
            if parent is None:
                Wp, Pp, hp = np.eye(3), h, h
                pm = False
            else:
                Pp, Wp = world[parent]
                hp = self.bones[parent][1]
                pm = moved[parent]
            P = Pp + Wp @ (h - hp)
            W = Wp @ locR[name] if name in locR else Wp
            world[name] = (P, W)
            moved[name] = pm or name in locR
        out = V.copy()
        acc = np.zeros_like(V)
        wsum = np.zeros(len(V))
        for name, (idx, wv) in self.w.items():
            if not moved.get(name):
                continue
            P, W = world[name]
            h = self.bones[name][1]
            acc[idx] += wv[:, None] * ((V[idx] - h) @ W.T + P)
            wsum[idx] += wv
        touched = wsum > 1e-9
        out[touched] = (acc[touched]
                        + (1 - wsum[touched])[:, None] * V[touched])
        return out


def _mirror(spec):
    """Swap .L and .R and flip the y/z rotation senses — the same pose on
    the other foot."""
    out = {}
    for bone, rots in spec.items():
        if bone.endswith(".L"):
            b2 = bone[:-2] + ".R"
        elif bone.endswith(".R"):
            b2 = bone[:-2] + ".L"
        else:
            b2 = bone
        out[b2] = [(a, d if a == "x" else -d) for a, d in rots]
    return out


# ---------------------------------------------------------------------------
# The keyframes. Angles in degrees about world-aligned rest axes; on this
# model +X rotation takes an up-pointing bone forward and a down-pointing
# bone backward, so hip flexion is negative and knee flexion positive.

SIT = {
    "root": [("x", -6)],
    "spine02": [("x", 10)],
    "neck01": [("x", 6)],
    "head": [("x", 8)],
    "upperleg01.L": [("x", -78), ("z", 7)],
    "upperleg01.R": [("x", -78), ("z", -7)],
    "lowerleg01.L": [("x", 82)],
    "lowerleg01.R": [("x", 82)],
    "foot.L": [("x", -6)],
    "foot.R": [("x", -6)],
    "upperarm01.L": [("x", -14), ("z", -12)],
    "upperarm01.R": [("x", -14), ("z", 12)],
    "lowerarm01.L": [("x", -48)],
    "lowerarm01.R": [("x", -48)],
}

RISE = {
    "spine05": [("x", 22)],
    "spine03": [("x", 16)],
    "neck01": [("x", -10)],
    "head": [("x", -10)],
    "upperleg01.L": [("x", -64), ("z", 5)],
    "upperleg01.R": [("x", -64), ("z", -5)],
    "lowerleg01.L": [("x", 62)],
    "lowerleg01.R": [("x", 62)],
    "foot.L": [("x", -4)],
    "foot.R": [("x", -4)],
    "upperarm01.L": [("x", 24)],
    "upperarm01.R": [("x", 24)],
    "lowerarm01.L": [("x", -42)],
    "lowerarm01.R": [("x", -42)],
}

WALK_A = {
    "spine03": [("x", 4)],
    "upperleg01.L": [("x", -26)],
    "lowerleg01.L": [("x", 10)],
    "foot.L": [("x", -8)],
    "upperleg01.R": [("x", 13)],
    "lowerleg01.R": [("x", 30)],
    "foot.R": [("x", 14)],
    "upperarm01.R": [("x", -20)],
    "lowerarm01.R": [("x", -22)],
    "upperarm01.L": [("x", 16)],
    "lowerarm01.L": [("x", -8)],
}
WALK_B = _mirror(WALK_A)

RUN_A = {
    "spine05": [("x", 9)],
    "spine03": [("x", 6)],
    "neck01": [("x", -5)],
    "head": [("x", -6)],
    "upperleg01.L": [("x", -48)],
    "lowerleg01.L": [("x", 42)],
    "foot.L": [("x", 4)],
    "upperleg01.R": [("x", 16)],
    "lowerleg01.R": [("x", 96)],
    "foot.R": [("x", 22)],
    "upperarm01.R": [("x", -38)],
    "lowerarm01.R": [("x", -82)],
    "upperarm01.L": [("x", 28)],
    "lowerarm01.L": [("x", -74)],
}
RUN_B = _mirror(RUN_A)

POSES = [("sit", SIT), ("rise", RISE), ("walkA", WALK_A),
         ("walkB", WALK_B), ("runA", RUN_A), ("runB", RUN_B)]
