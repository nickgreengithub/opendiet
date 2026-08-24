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

# The bottom of the scale: sunk into a recliner with a TV remote — legs up
# on the footrest, torso tipped back, the right forearm raised to point the
# remote, the left draped on the armrest. Face level, at the television.
RECLINE = {
    "spine05": [("x", -20)],
    "spine03": [("x", -12)],
    "neck01": [("x", 10)],
    "head": [("x", 14)],
    "upperleg01.L": [("x", -68), ("z", 6)],
    "upperleg01.R": [("x", -68), ("z", -6)],
    "lowerleg01.L": [("x", 30)],
    "lowerleg01.R": [("x", 30)],
    "foot.L": [("x", 20)],
    "foot.R": [("x", 20)],
    "upperarm01.L": [("x", -2)],
    "upperarm01.R": [("x", -18)],
    "lowerarm01.L": [("x", -12)],
    "lowerarm01.R": [("x", -42)],
}

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

# Gait twist: the pelvis turns with the leading leg (negative y takes the
# left hip forward), the shoulders counter-rotate past it with the leading
# arm, and the neck and head unwind the difference so the face stays on the
# road. The mirror flips the y senses with the sides.
WALK_A = {
    "root": [("y", -4)],
    "spine02": [("y", 5)],
    "spine01": [("y", 3)],
    "spine03": [("x", 4)],
    "neck01": [("y", -3)],
    "head": [("y", -2)],
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

# What made the first run comical: the arms swung hardly at all while the
# elbows stayed locked at ninety, so the hands rode up at the chest like
# paws — and the wrists were never posed, leaving the fingers splayed at
# face height. The rebuilt stride swings the whole arm from the shoulder
# with the elbow opening on the back-swing, curls the wrists loosely,
# drives the rear hip further into extension, and dorsiflexes the leading
# foot for the strike instead of letting it dangle.
RUN_A = {
    "root": [("y", -8)],
    "spine05": [("x", 12)],
    "spine03": [("x", 7)],
    "spine02": [("y", 9)],
    "spine01": [("y", 7)],
    "neck01": [("x", -7), ("y", -5)],
    "head": [("x", -8), ("y", -4)],
    "upperleg01.L": [("x", -52)],
    "lowerleg01.L": [("x", 48)],
    "foot.L": [("x", -12)],
    "upperleg01.R": [("x", 26)],
    "lowerleg01.R": [("x", 102)],
    "foot.R": [("x", 30)],
    "shoulder01.R": [("x", -8)],
    "upperarm01.R": [("x", -48)],
    "lowerarm01.R": [("x", -66)],
    "wrist.R": [("x", -28)],
    "shoulder01.L": [("x", 6)],
    "upperarm01.L": [("x", 36)],
    "lowerarm01.L": [("x", -48)],
    "wrist.L": [("x", -28)],
}
RUN_B = _mirror(RUN_A)

def _fist(spec, curl=55):
    """Curl the fingers of both hands around a bar — every segment of the
    four fingers takes a share of the curl, the thumb wraps less."""
    for side in ("L", "R"):
        for f in range(2, 6):
            for seg in range(1, 4):
                spec["finger%d-%d.%s" % (f, seg, side)] = [("x", -curl)]
        spec["finger1-2.%s" % side] = [("x", -30)]
        spec["finger1-3.%s" % side] = [("x", -35)]
    return spec


# The runner's hands close loosely — the curl is all x, so it survives the
# mirror that made RUN_B before this helper existed.
_fist(RUN_A, curl=48)
_fist(RUN_B, curl=48)


# The incline press, in two keyframes the runtime swings between. The
# figure sits into an incline bench — torso laid back, feet planted wide —
# and presses perpendicular to the pad: elbows flared at the chest at the
# bottom, arms locked out over the upper chest at the top. The shoulder
# girdle carries part of each arm's arc so the deltoid doesn't crease.
PRESS_DN = {
    "spine05": [("x", -34)],
    "spine03": [("x", -10)],
    "neck01": [("x", 5)],
    "head": [("x", 7)],
    "upperleg01.L": [("x", -74), ("z", 12)],
    "upperleg01.R": [("x", -74), ("z", -12)],
    "lowerleg01.L": [("x", 80)],
    "lowerleg01.R": [("x", 80)],
    "foot.L": [("x", -6)],
    "foot.R": [("x", -6)],
    "shoulder01.L": [("x", -14)],
    "shoulder01.R": [("x", -14)],
    "upperarm01.L": [("x", -56), ("z", -26)],
    "upperarm01.R": [("x", -56), ("z", 26)],
    "lowerarm01.L": [("x", -64), ("z", 18)],
    "lowerarm01.R": [("x", -64), ("z", -18)],
    "wrist.L": [("x", -12)],
    "wrist.R": [("x", -12)],
}
_fist(PRESS_DN)
PRESS_UP = {
    "spine05": [("x", -34)],
    "spine03": [("x", -10)],
    "neck01": [("x", 5)],
    "head": [("x", 7)],
    "upperleg01.L": [("x", -74), ("z", 12)],
    "upperleg01.R": [("x", -74), ("z", -12)],
    "lowerleg01.L": [("x", 80)],
    "lowerleg01.R": [("x", 80)],
    "foot.L": [("x", -6)],
    "foot.R": [("x", -6)],
    "shoulder01.L": [("x", -22)],
    "shoulder01.R": [("x", -22)],
    "upperarm01.L": [("x", -88)],
    "upperarm01.R": [("x", -88)],
    "lowerarm01.L": [("x", -5)],
    "lowerarm01.R": [("x", -5)],
    "wrist.L": [("x", -12)],
    "wrist.R": [("x", -12)],
}
_fist(PRESS_UP)

POSES = [("recline", RECLINE), ("sit", SIT), ("rise", RISE),
         ("walkA", WALK_A), ("walkB", WALK_B), ("runA", RUN_A),
         ("runB", RUN_B), ("pressDn", PRESS_DN), ("pressUp", PRESS_UP)]
