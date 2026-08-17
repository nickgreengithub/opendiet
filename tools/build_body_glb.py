#!/usr/bin/env python3
"""Generate the placeholder body meshes the calc app morphs.

This is a stand-in for MB-Lab. It writes a glTF 2.0 binary (.glb) holding one
lofted humanoid with a stack of morph targets, one per body-fat level — exactly
the shape of file the MB-Lab bake produces, so when the real export lands it
drops into the same loader with no code change.

    python3 tools/build_body_glb.py

Writes data/body/body-m.glb and data/body/body-f.glb.

The contract the runtime relies on, and which any replacement must honour:

  * one mesh, one primitive, POSITION + NORMAL, indexed triangles
  * the BASE mesh is the leanest level
  * N morph targets in ascending order of body fat, each with POSITION and
    NORMAL deltas
  * mesh.extras.bodyFat lists the body-fat percentage of the base and of every
    target, in the same order, so the runtime can build its blend without
    knowing anything about how the file was made
  * Y up, metres, feet at y=0, facing +Z
"""

import json
import math
import os
import struct

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "body")

SEG = 20          # segments around each ring
LEVELS = [8, 15, 22, 30, 38, 46]   # body-fat % — the first is the base mesh


# ── the body, as stacks of rings ──────────────────────────────────────────────
# Each ring is (y, rx, rz, cx, w, fz).
#
#   y, rx, rz  height and the two radii of its ellipse
#   cx         how far off centre it sits
#   w          how strongly fat lands here — abdomen first in men, hips and
#              thighs in women, and almost nowhere else
#   fz         how far the ring pushes FORWARD only
#
# fz is what makes a chest a chest. An ellipse that is deep front-to-back bulges
# backwards as much as forwards, which on a woman reads as a chest on both sides
# and on a heavy man reads as a barrel. A one-sided bulge is a bust, or a belly.

TORSO_M = [
    # y      rx     rz     cx    w     fz
    (0.88, 0.072, 0.062, 0.0, 1.05, 0.000),   # crotch
    (0.93, 0.154, 0.106, 0.0, 1.20, 0.000),
    (0.96, 0.166, 0.120, 0.0, 1.30, 0.004),   # hips — narrow
    (1.04, 0.152, 0.114, 0.0, 1.65, 0.020),
    (1.12, 0.143, 0.106, 0.0, 1.95, 0.032),   # waist — the belly, forward
    (1.20, 0.158, 0.114, 0.0, 1.55, 0.018),
    (1.28, 0.182, 0.126, 0.0, 1.00, 0.008),   # chest
    (1.36, 0.212, 0.126, 0.0, 0.65, 0.000),
    (1.43, 0.232, 0.116, 0.0, 0.50, 0.000),   # shoulders — wide
    (1.485, 0.090, 0.086, 0.0, 0.45, 0.000),  # trapezius into the neck
    (1.55, 0.058, 0.058, 0.0, 0.40, 0.000),
    (1.60, 0.076, 0.090, 0.0, 0.45, 0.010),   # jaw
    (1.66, 0.095, 0.104, 0.0, 0.30, 0.006),
    (1.72, 0.070, 0.076, 0.0, 0.20, 0.000),
    (1.750, 0.016, 0.016, 0.0, 0.10, 0.000),
]

TORSO_F = [
    (0.88, 0.074, 0.064, 0.0, 1.55, 0.000),   # crotch
    (0.93, 0.168, 0.114, 0.0, 1.50, 0.000),
    (0.96, 0.182, 0.130, 0.0, 1.55, 0.000),   # hips — wide
    (1.04, 0.160, 0.118, 0.0, 1.40, 0.006),
    (1.12, 0.124, 0.100, 0.0, 1.20, 0.014),   # waist — narrow
    (1.20, 0.132, 0.104, 0.0, 1.15, 0.012),
    (1.28, 0.142, 0.104, 0.0, 1.05, 0.056),   # bust — forward, not sideways
    (1.36, 0.160, 0.112, 0.0, 0.70, 0.008),
    (1.43, 0.174, 0.106, 0.0, 0.50, 0.000),   # shoulders — narrow
    (1.485, 0.076, 0.074, 0.0, 0.45, 0.000),
    (1.55, 0.049, 0.049, 0.0, 0.40, 0.000),   # neck — slender
    (1.60, 0.068, 0.082, 0.0, 0.45, 0.008),
    (1.66, 0.088, 0.096, 0.0, 0.30, 0.005),
    (1.72, 0.064, 0.070, 0.0, 0.20, 0.000),
    (1.750, 0.016, 0.016, 0.0, 0.10, 0.000),
]

# The thighs now begin at the hip rather than below it, and at the hip they are
# as wide as the pelvis is. Starting them lower and narrower is what made them
# read as two posts propped under a torso rather than part of one body.
LEG_M = [
    (1.02, 0.088, 0.088, 0.085, 1.25, 0.000),
    (0.94, 0.099, 0.099, 0.085, 1.40, 0.000),
    (0.86, 0.096, 0.098, 0.084, 1.55, 0.000),   # thigh
    (0.70, 0.082, 0.085, 0.084, 1.30, 0.000),
    (0.54, 0.061, 0.065, 0.086, 0.85, 0.000),   # knee
    (0.42, 0.068, 0.071, 0.088, 0.95, 0.000),   # calf
    (0.24, 0.050, 0.053, 0.090, 0.60, 0.000),
    (0.09, 0.037, 0.040, 0.092, 0.35, 0.000),   # ankle
    (0.015, 0.046, 0.060, 0.092, 0.25, 0.055),  # foot, pointing forward
]

LEG_F = [
    (1.02, 0.094, 0.094, 0.095, 1.45, 0.000),
    (0.94, 0.105, 0.103, 0.097, 1.55, 0.000),
    (0.86, 0.103, 0.104, 0.098, 1.70, 0.000),   # thigh
    (0.70, 0.083, 0.086, 0.097, 1.35, 0.000),
    (0.54, 0.057, 0.061, 0.095, 0.85, 0.000),
    (0.42, 0.063, 0.066, 0.094, 0.95, 0.000),
    (0.24, 0.045, 0.048, 0.093, 0.55, 0.000),
    (0.09, 0.033, 0.036, 0.092, 0.35, 0.000),
    (0.015, 0.042, 0.056, 0.092, 0.25, 0.050),
]

# Arms hang against the body rather than out from it.
ARM_M = [
    (1.46, 0.050, 0.050, 0.204, 0.70, 0.000),   # buried in the shoulder
    (1.40, 0.058, 0.058, 0.211, 0.70, 0.000),
    (1.28, 0.052, 0.052, 0.219, 0.85, 0.000),   # upper arm
    (1.14, 0.045, 0.045, 0.226, 0.75, 0.000),
    (1.05, 0.040, 0.040, 0.231, 0.55, 0.000),   # elbow
    (0.95, 0.037, 0.037, 0.235, 0.55, 0.000),
    (0.84, 0.028, 0.028, 0.239, 0.35, 0.000),   # wrist
    (0.74, 0.033, 0.028, 0.241, 0.25, 0.000),   # hand
]

ARM_F = [
    (1.46, 0.039, 0.039, 0.152, 0.75, 0.000),
    (1.40, 0.045, 0.045, 0.158, 0.75, 0.000),
    (1.28, 0.040, 0.040, 0.166, 0.95, 0.000),
    (1.14, 0.034, 0.034, 0.173, 0.80, 0.000),
    (1.05, 0.030, 0.030, 0.178, 0.55, 0.000),
    (0.95, 0.028, 0.028, 0.182, 0.55, 0.000),
    (0.84, 0.022, 0.022, 0.186, 0.35, 0.000),
    (0.74, 0.028, 0.023, 0.188, 0.25, 0.000),
]


def loft(rings, mirror, fat):
    """One tube of rings into (verts, tris). fat is (bf - base)/100."""
    verts, tris = [], []
    sign = -1.0 if mirror else 1.0
    for (y, rx, rz, cx, w, fz) in rings:
        # Radii grow with fat, weighted by where on the body the ring sits.
        #
        # The coefficient is not free. Going from 8% body fat to 46% at constant
        # lean mass is about 1.7x the body mass, so about 1.7x the volume; at a
        # fixed height that is 1.3x the radius if it landed evenly. It does not
        # land evenly, so the places that take it reach about 1.7x and the limbs
        # about 1.15x, which averages back to roughly the right body.
        k = 1.0 + max(-0.45, fat * w * 0.98)
        kz = 1.0 + max(-0.45, fat * w * 1.22)   # depth grows faster than width
        # The forward bulge grows with fat too — a belly is not a wider waist, it
        # is a waist that comes out at the front.
        kf = 1.0 + max(-0.7, fat * w * 1.7)
        for i in range(SEG):
            a = 2.0 * math.pi * i / SEG
            sa, ca = math.sin(a), math.cos(a)
            front = sa * sa if sa > 0 else 0.0
            verts.append((sign * cx + rx * k * ca, y, rz * kz * sa + fz * kf * front))
    for r in range(len(rings) - 1):
        for i in range(SEG):
            a0 = r * SEG + i
            a1 = r * SEG + (i + 1) % SEG
            b0 = a0 + SEG
            b1 = a1 + SEG
            if mirror:
                tris += [(a0, a1, b1), (a0, b1, b0)]
            else:
                tris += [(a0, b1, a1), (a0, b0, b1)]
    return verts, tris


def cap(verts, tris, ring_start, flip):
    """Close a tube end with a fan to its centroid."""
    cx = sum(verts[ring_start + i][0] for i in range(SEG)) / SEG
    cy = sum(verts[ring_start + i][1] for i in range(SEG)) / SEG
    cz = sum(verts[ring_start + i][2] for i in range(SEG)) / SEG
    c = len(verts)
    verts.append((cx, cy, cz))
    for i in range(SEG):
        a = ring_start + i
        b = ring_start + (i + 1) % SEG
        tris.append((c, b, a) if flip else (c, a, b))
    return c


def build(sex, fat):
    torso = TORSO_F if sex == "f" else TORSO_M
    leg = LEG_F if sex == "f" else LEG_M
    arm = ARM_F if sex == "f" else ARM_M
    verts, tris = [], []
    # (cap_start, cap_end): the torso closes at both ends — crown and crotch — and
    # the legs are open at the top because the torso already fills that space.
    for rings, mirror, caps in ((torso, False, (True, True)),
                               (leg, False, (True, True)), (leg, True, (True, True)),
                               (arm, False, (True, True)), (arm, True, (True, True))):
        off = len(verts)
        v, t = loft(rings, mirror, fat)
        verts += v
        tris += [(a + off, b + off, c + off) for (a, b, c) in t]
        if caps[0]:
            cap(verts, tris, off, mirror)
        if caps[1]:
            cap(verts, tris, off + (len(rings) - 1) * SEG, not mirror)
    return verts, tris


def normals(verts, tris):
    n = [[0.0, 0.0, 0.0] for _ in verts]
    for (a, b, c) in tris:
        ax, ay, az = verts[a]
        bx, by, bz = verts[b]
        cx, cy, cz = verts[c]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        fx, fy, fz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        for i in (a, b, c):
            n[i][0] += fx
            n[i][1] += fy
            n[i][2] += fz
    out = []
    for (x, y, z) in n:
        m = math.sqrt(x * x + y * y + z * z) or 1.0
        out.append((x / m, y / m, z / m))
    return out


def pad4(b, fill=b"\x00"):
    """glTF chunks are 4-byte aligned. The JSON chunk must be padded with SPACES,
    not nulls — a JSON parser will choke on a trailing NUL, and it only shows up
    when the payload length happens not to already be a multiple of four."""
    return b + fill * ((4 - len(b) % 4) % 4)


def write_glb(path, sex):
    base_bf = LEVELS[0]
    base_v, tris = build(sex, 0.0)
    base_n = normals(base_v, tris)

    shapes = []
    for bf in LEVELS[1:]:
        v, _ = build(sex, (bf - base_bf) / 100.0)
        shapes.append((v, normals(v, tris)))

    buf = bytearray()
    views, accs = [], []

    def add(data, target, comp, typ, count, mn=None, mx=None):
        while len(buf) % 4:
            buf.append(0)
        off = len(buf)
        buf.extend(data)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data)}
                     | ({"target": target} if target else {}))
        a = {"bufferView": len(views) - 1, "componentType": comp,
             "count": count, "type": typ}
        if mn:
            a["min"], a["max"] = mn, mx
        accs.append(a)
        return len(accs) - 1

    def vec3(vs):
        d = bytearray()
        mn = [1e9] * 3
        mx = [-1e9] * 3
        for v in vs:
            d.extend(struct.pack("<3f", *v))
            for i in range(3):
                mn[i] = min(mn[i], v[i])
                mx[i] = max(mx[i], v[i])
        return bytes(d), mn, mx

    d, mn, mx = vec3(base_v)
    a_pos = add(d, 34962, 5126, "VEC3", len(base_v), mn, mx)
    d, _, _ = vec3(base_n)
    a_nrm = add(d, 34962, 5126, "VEC3", len(base_n))
    idx = bytearray()
    for t in tris:
        idx.extend(struct.pack("<3I", *t))
    a_idx = add(bytes(idx), 34963, 5125, "SCALAR", len(tris) * 3)

    targets = []
    for (v, n) in shapes:
        dv = [(v[i][0] - base_v[i][0], v[i][1] - base_v[i][1], v[i][2] - base_v[i][2])
              for i in range(len(v))]
        dn = [(n[i][0] - base_n[i][0], n[i][1] - base_n[i][1], n[i][2] - base_n[i][2])
              for i in range(len(n))]
        d, mn, mx = vec3(dv)
        tp = add(d, 34962, 5126, "VEC3", len(dv), mn, mx)
        d, _, _ = vec3(dn)
        tn = add(d, 34962, 5126, "VEC3", len(dn))
        targets.append({"POSITION": tp, "NORMAL": tn})

    gltf = {
        "asset": {"version": "2.0", "generator": "opendiet/build_body_glb.py"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "body"}],
        "meshes": [{
            "name": "body",
            "weights": [0.0] * len(targets),
            "primitives": [{
                "attributes": {"POSITION": a_pos, "NORMAL": a_nrm},
                "indices": a_idx,
                "targets": targets
            }],
            "extras": {
                "bodyFat": LEVELS,
                "sex": sex,
                "targetNames": ["bf%d" % b for b in LEVELS[1:]]
            }
        }],
        "accessors": accs,
        "bufferViews": views,
        "buffers": [{"byteLength": len(buf)}]
    }

    js = pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bn = pad4(bytes(buf))
    total = 12 + 8 + len(js) + 8 + len(bn)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack("<II", len(bn), 0x004E4942))
        f.write(bn)
    return len(base_v), len(tris), total


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for sex in ("m", "f"):
        p = os.path.join(OUT, "body-%s.glb" % sex)
        nv, nt, sz = write_glb(p, sex)
        print("%s  %d verts  %d tris  %d morph targets  %.0f KB"
              % (os.path.relpath(p, HERE), nv, nt, len(LEVELS) - 1, sz / 1024.0))
