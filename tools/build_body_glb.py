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
# Each ring is (y, rx, rz, cx, w) — height, the two radii of its ellipse, how far
# it is off centre, and w, how strongly fat lands there. w is the whole reason
# this reads as a body changing rather than a balloon inflating: fat goes to the
# abdomen first in men and to the hips and thighs in women, and everywhere else
# it barely moves.

# Male and female are now properly dimorphic rather than the same body at two
# slightly different widths. The shoulder-to-hip ratio does most of the work —
# about 1.47 for the male and 0.90 for the female — with the waist, the bust and
# the stance carrying the rest. At a glance, from across a room, that is what
# tells you which body you are looking at.

TORSO_M = [
    # y      rx     rz     cx     w
    (0.80, 0.055, 0.048, 0.0, 1.05),   # crotch
    (0.86, 0.115, 0.088, 0.0, 1.20),
    (0.91, 0.150, 0.116, 0.0, 1.30),
    (0.96, 0.158, 0.128, 0.0, 1.35),   # hips — narrow
    (1.04, 0.148, 0.120, 0.0, 1.70),
    (1.12, 0.140, 0.112, 0.0, 1.95),   # waist — the first place it goes
    (1.20, 0.157, 0.120, 0.0, 1.60),
    (1.28, 0.182, 0.132, 0.0, 1.05),   # chest
    (1.36, 0.212, 0.130, 0.0, 0.70),
    (1.43, 0.234, 0.120, 0.0, 0.55),   # shoulders — wide
    (1.49, 0.096, 0.092, 0.0, 0.45),   # neck base, thick
    (1.55, 0.063, 0.063, 0.0, 0.40),
    (1.60, 0.080, 0.094, 0.0, 0.45),   # jaw, square
    (1.66, 0.098, 0.107, 0.0, 0.30),
    (1.72, 0.073, 0.079, 0.0, 0.20),
    (1.750, 0.016, 0.016, 0.0, 0.10),
]

TORSO_F = [
    (0.80, 0.058, 0.050, 0.0, 1.70),   # crotch
    (0.86, 0.127, 0.096, 0.0, 1.35),
    (0.91, 0.170, 0.130, 0.0, 1.45),
    (0.96, 0.184, 0.144, 0.0, 1.55),   # hips — wide, and where it goes first
    (1.04, 0.164, 0.130, 0.0, 1.45),
    (1.12, 0.126, 0.104, 0.0, 1.25),   # waist — narrow
    (1.20, 0.132, 0.114, 0.0, 1.25),
    (1.28, 0.152, 0.142, 0.0, 1.05),   # bust — deeper than it is wide
    (1.36, 0.166, 0.120, 0.0, 0.75),
    (1.43, 0.176, 0.108, 0.0, 0.55),   # shoulders — narrow
    (1.49, 0.080, 0.078, 0.0, 0.45),
    (1.55, 0.052, 0.052, 0.0, 0.40),   # neck, slender
    (1.60, 0.071, 0.085, 0.0, 0.45),
    (1.66, 0.091, 0.099, 0.0, 0.30),
    (1.72, 0.067, 0.073, 0.0, 0.20),
    (1.750, 0.016, 0.016, 0.0, 0.10),
]

LEG_M = [
    # The first two rings are narrower than the torso at the same height, because a
    # leg that is wider than the pelvis it hangs off shows its rim as a flange and
    # you can see straight down the tube.
    (1.05, 0.062, 0.062, 0.070, 1.30),
    (0.97, 0.090, 0.092, 0.077, 1.40),
    (0.86, 0.096, 0.098, 0.082, 1.55),   # thigh
    (0.70, 0.082, 0.085, 0.084, 1.30),
    (0.54, 0.061, 0.065, 0.086, 0.85),   # knee
    (0.42, 0.068, 0.071, 0.088, 0.95),   # calf
    (0.24, 0.050, 0.053, 0.090, 0.60),
    (0.09, 0.037, 0.040, 0.092, 0.35),   # ankle
    (0.015, 0.048, 0.075, 0.092, 0.25),  # foot
]

LEG_F = [
    (1.05, 0.066, 0.066, 0.082, 1.45),
    (0.97, 0.098, 0.098, 0.093, 1.55),
    (0.86, 0.103, 0.104, 0.099, 1.70),   # thigh — the other place it goes
    (0.70, 0.083, 0.086, 0.097, 1.35),
    (0.54, 0.057, 0.061, 0.095, 0.85),
    (0.42, 0.063, 0.066, 0.094, 0.95),
    (0.24, 0.045, 0.048, 0.093, 0.55),
    (0.09, 0.033, 0.036, 0.092, 0.35),
    (0.015, 0.043, 0.069, 0.092, 0.25),
]

ARM_M = [
    (1.45, 0.052, 0.052, 0.212, 0.70),   # buried inside the shoulder
    (1.40, 0.060, 0.060, 0.220, 0.70),
    (1.28, 0.053, 0.053, 0.231, 0.85),   # upper arm
    (1.14, 0.046, 0.046, 0.240, 0.75),
    (1.05, 0.041, 0.041, 0.246, 0.55),   # elbow
    (0.95, 0.038, 0.038, 0.251, 0.55),
    (0.84, 0.029, 0.029, 0.256, 0.35),   # wrist
    (0.74, 0.035, 0.029, 0.259, 0.25),   # hand
]

ARM_F = [
    (1.45, 0.040, 0.040, 0.156, 0.75),
    (1.40, 0.046, 0.046, 0.163, 0.75),
    (1.28, 0.041, 0.041, 0.174, 0.95),
    (1.14, 0.035, 0.035, 0.183, 0.80),
    (1.05, 0.031, 0.031, 0.189, 0.55),
    (0.95, 0.029, 0.029, 0.194, 0.55),
    (0.84, 0.023, 0.023, 0.199, 0.35),
    (0.74, 0.029, 0.024, 0.202, 0.25),
]


def loft(rings, mirror, fat):
    """One tube of rings into (verts, tris). fat is (bf - base)/100."""
    verts, tris = [], []
    sign = -1.0 if mirror else 1.0
    for (y, rx, rz, cx, w) in rings:
        # Radii grow with fat, weighted by where on the body the ring sits.
        #
        # The coefficient is not free. Going from 8% body fat to 46% at constant
        # lean mass is about 1.7x the body mass, so about 1.7x the volume; at a
        # fixed height that is 1.3x the radius if it landed evenly. It does not
        # land evenly, so the places that take it reach about 1.7x and the limbs
        # about 1.15x, which averages back to roughly the right body.
        k = 1.0 + max(-0.45, fat * w * 0.98)
        kz = 1.0 + max(-0.45, fat * w * 1.22)   # depth grows faster than width
        for i in range(SEG):
            a = 2.0 * math.pi * i / SEG
            verts.append((sign * cx + rx * k * math.cos(a), y, rz * kz * math.sin(a)))
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
