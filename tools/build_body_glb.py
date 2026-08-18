#!/usr/bin/env python3
"""Generate the body meshes the calc app morphs.

This is still a stand-in for a sculpted mesh (MB-Lab via tools/mblab_bake.py),
but it is no longer a stack of lofted rings. The body is a signed distance
field: anatomical masses — ribcage, pelvis, glutes, breasts, deltoids, a head,
tapered limbs — blended into ONE continuous surface with smooth minimums. That
buys the three things a ring loft can never have:

  * concavities — a sternal valley, a waist, a gap between the thighs — because
    valleys appear naturally BETWEEN blended convex masses;
  * joints instead of intersections — a deltoid wraps the arm into the torso,
    a hip wraps the thigh into the pelvis, so there is no seam line for the eye
    to read as "two objects";
  * a pose — arms in a slight A-pose with a bent elbow, feet turned a little
    out, which is how a person stands rather than how a mannequin is stored.

The leanest body is meshed once with naive surface nets over a voxel grid; each
fatter level is then made by projecting THOSE SAME vertices onto the fatter
field (Newton steps along the gradient), so every level shares one topology and
ships as a glTF morph target.

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
import os
import struct
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "body")

# Per-sex fat levels: the female range starts near essential fat, which the
# app's slider also enforces, so no morph budget is spent on impossible bodies.
LEVELS = {"m": [8, 15, 22, 30, 38, 46], "f": [12, 18, 25, 32, 40, 48]}
VOX = 0.014          # voxel edge for the base mesh, metres


# ── SDF primitives, vectorised over an (N,3) array of points ──────────────────

def sd_ellipsoid(P, c, r):
    q = (P - np.asarray(c)) / np.asarray(r)
    k0 = np.linalg.norm(q, axis=1)
    k1 = np.linalg.norm(q / np.asarray(r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_sphere(P, c, r):
    return np.linalg.norm(P - np.asarray(c), axis=1) - r


def sd_roundcone(P, a, b, r1, r2):
    """A tapered capsule — the natural shape of a limb segment (Quilez)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ba = b - a
    l2 = float(ba @ ba)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = P - a
    y = pa @ ba
    z = y - l2
    w = pa * l2 - np.outer(y, ba)
    x2 = np.einsum("ij,ij->i", w, w)
    z2 = z * z * l2
    y2 = y * y * l2
    k = np.sign(rr) * rr * rr * x2
    d = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
    d = np.where(np.sign(z) * a2 * z2 > k,
                 np.sqrt(np.maximum(x2 + z2, 0)) * il2 - r2, d)
    d = np.where(np.sign(y) * a2 * y2 < k,
                 np.sqrt(np.maximum(x2 + y2, 0)) * il2 - r1, d)
    return d


def smin(a, b, k):
    """Polynomial smooth minimum: the flesh between two masses."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


# ── the body ──────────────────────────────────────────────────────────────────
# Positions in metres: feet at y=0, crown near 1.75, +z forward. f is fat as a
# 0..1 fraction across this sex's LEVELS span. Each mass grows by its own
# factor — abdomen first on a man, hips, thighs and bust on a woman — and a
# thin "skin" offset inflates everything else a little.

def sdf_body(P, sex, f):
    m = sex == "m"
    E, S, RC = sd_ellipsoid, sd_sphere, sd_roundcone

    def g(base, gain):                 # a dimension that grows with fat
        return base * (1.0 + gain * f)

    shx = 0.180 if m else 0.148        # shoulder joint x
    hipx = 0.086 if m else 0.094       # hip joint x

    # torso chain: ribcage → abdomen → pelvis. The waist is not drawn — it is
    # the narrowness of the abdomen between two wider masses.
    d = E(P, (0, 1.315, 0.005),
          (g(0.148 if m else 0.120, 0.10), 0.155,
           g(0.106 if m else 0.092, 0.18)))
    d = smin(d, E(P, (0, 1.115 - f * 0.030, 0.008 + f * (0.046 if m else 0.022)),
                  (g(0.108 if m else 0.096, 0.95 if m else 0.95),
                   0.135,
                   g(0.085 if m else 0.078, 1.40 if m else 0.75))), 0.065)
    d = smin(d, E(P, (0, 0.965, 0.0),
                  (g(0.120 if m else 0.140, 0.42 if m else 0.55),
                   0.118,
                   g(0.090 if m else 0.094, 0.45 if m else 0.50))), 0.068)

    # glutes: two masses, so the surface between them is a real crease.
    gr = g(0.059 if m else 0.058, 0.55 if m else 0.70)
    gz = -0.052 - f * 0.010
    d = smin(d, S(P, (+0.056, 0.975, gz), gr), 0.065)
    d = smin(d, S(P, (-0.056, 0.975, gz), gr), 0.065)

    # upper chest, so the clavicle region is a plane rather than a hollow.
    d = smin(d, E(P, (0, 1.400, 0.026),
                  (0.104 if m else 0.088, 0.058, 0.048)), 0.050)

    # chest: pectorals on a man, a bust on a woman. Two masses either way, and
    # the sternal valley between them is the blend refusing to fill it.
    if m:
        pr = (0.066, 0.054, g(0.048, 0.8))
        d = smin(d, E(P, (+0.063, 1.338, 0.066), pr), 0.045)
        d = smin(d, E(P, (-0.063, 1.338, 0.066), pr), 0.045)
    else:
        br = g(0.051, 0.72)
        bz = 0.072 + f * 0.018
        d = smin(d, E(P, (+0.053, 1.312, bz),
                      (br, br * 0.95, g(0.048, 0.75))), 0.048)
        d = smin(d, E(P, (-0.053, 1.312, bz),
                      (br, br * 0.95, g(0.048, 0.75))), 0.048)
        d = smin(d, E(P, (0, 1.298, bz - 0.014),
                      (0.052, br * 0.85, g(0.038, 0.7))), 0.055)

    # trapezius: the slope from neck to shoulder that a tube body never has.
    tx = 0.97 if m else 0.78          # a man's trapezius rounds over the shoulder
    d = smin(d, RC(P, (0.015, 1.486, -0.008),
                   (+shx * tx, 1.424, -0.004), 0.026, 0.036 if m else 0.027), 0.050)
    d = smin(d, RC(P, (-0.015, 1.486, -0.008),
                   (-shx * tx, 1.424, -0.004), 0.026, 0.036 if m else 0.027), 0.050)

    # arms: deltoid, upper arm, forearm, hand, in a slight A-pose with a bent
    # elbow. The deltoid joins the arm to the body instead of crossing it.
    ao = f * 0.055                     # a wider body pushes the arms out
    for sgn in (+1.0, -1.0):
        sh = (sgn * (shx + 0.004 + ao * 0.5), 1.408, 0.004)
        wr = (sgn * (shx + 0.074 + ao), 0.885, 0.020)
        d = smin(d, RC(P, sh, wr, g(0.051 if m else 0.042, 0.38),
                       g(0.023 if m else 0.018, 0.25)), 0.040)
        d = smin(d, E(P, (wr[0] + sgn * 0.002, 0.800, 0.026),
                      (0.019, 0.064, 0.026)), 0.024)

    # neck and head.
    d = smin(d, RC(P, (0, 1.445, -0.006), (0, 1.590, 0.002),
                   g(0.051 if m else 0.043, 0.50),
                   0.046 if m else 0.040), 0.040)
    d = smin(d, E(P, (0, 1.652, -0.004),
                  (0.079 if m else 0.075, 0.104, 0.092)), 0.045)
    d = smin(d, E(P, (0, 1.588, 0.038),
                  (0.058 if m else 0.053, g(0.042, 0.35), 0.052)), 0.030)

    # legs: thigh into the pelvis, a knee, a calf with a belly, an ankle, a
    # foot pointing forward and a little out.
    for sgn in (+1.0, -1.0):
        hip = (sgn * hipx, 0.965, 0.0)
        knee = (sgn * (hipx + 0.006), 0.505, -0.004)
        ank = (sgn * (hipx + 0.012), 0.078, -0.018)
        d = smin(d, RC(P, hip, knee,
                       g(0.079 if m else 0.078, 0.55 if m else 1.00),
                       g(0.052, 0.18)), 0.060)
        d = smin(d, S(P, (knee[0], 0.505, 0.0), 0.038), 0.055)
        d = smin(d, RC(P, knee, ank, 0.048, 0.025), 0.040)
        d = smin(d, E(P, (knee[0] + sgn * 0.002, 0.385, -0.022),
                      (0.043, 0.085, g(0.049, 0.30))), 0.035)
        d = smin(d, E(P, (ank[0] + sgn * 0.010, 0.034, 0.048),
                      (0.036, 0.034, 0.100)), 0.028)

    # subcutaneous layer: everything gains a little, so a fat wrist and a fat
    # jaw exist without their own masses.
    return d - (0.002 + 0.011 * f)


# ── meshing: naive surface nets over a voxel grid ────────────────────────────

CUBE = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
        (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
EDGES = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7),
         (0, 4), (1, 5), (2, 6), (3, 7)]


def surface_nets(sdf, lo, hi, h):
    xs = np.arange(lo[0], hi[0] + h, h)
    ys = np.arange(lo[1], hi[1] + h, h)
    zs = np.arange(lo[2], hi[2] + h, h)
    GX, GY, GZ = np.meshgrid(xs, ys, zs, indexing="ij")
    P = np.stack([GX.ravel(), GY.ravel(), GZ.ravel()], axis=1)
    F = sdf(P).reshape(GX.shape)
    nx, ny, nz = F.shape[0] - 1, F.shape[1] - 1, F.shape[2] - 1

    corner = [F[dx:dx + nx, dy:dy + ny, dz:dz + nz] for (dx, dy, dz) in CUBE]
    mn = np.minimum.reduce(corner)
    mx = np.maximum.reduce(corner)
    cells = np.argwhere((mn < 0) & (mx >= 0))

    # one vertex per surface cell, at the mean of its edge crossings
    cid = -np.ones((nx, ny, nz), dtype=np.int64)
    verts = np.zeros((len(cells), 3))
    for n, (i, j, k) in enumerate(cells):
        cid[i, j, k] = n
        acc = np.zeros(3)
        cnt = 0
        fv = [F[i + dx, j + dy, k + dz] for (dx, dy, dz) in CUBE]
        pv = [(xs[i + dx], ys[j + dy], zs[k + dz]) for (dx, dy, dz) in CUBE]
        for (a, b) in EDGES:
            fa, fb = fv[a], fv[b]
            if (fa < 0) != (fb < 0):
                t = fa / (fa - fb)
                pa, pb = np.array(pv[a]), np.array(pv[b])
                acc += pa + t * (pb - pa)
                cnt += 1
        verts[n] = acc / max(cnt, 1)

    # one quad per sign-changing sample edge, joining the four cells around it
    tris = []

    def emit(c4, flip):
        a, b, c, dq = c4
        if a < 0 or b < 0 or c < 0 or dq < 0:
            return
        quad = (a, dq, c, b) if flip else (a, b, c, dq)
        tris.append((quad[0], quad[1], quad[2]))
        tris.append((quad[0], quad[2], quad[3]))

    cross = (F[:-1, :, :] < 0) != (F[1:, :, :] < 0)
    for (i, j, k) in np.argwhere(cross):
        if 1 <= j <= ny - 1 and 1 <= k <= nz - 1 and i <= nx - 1:
            emit((cid[i, j, k], cid[i, j - 1, k],
                  cid[i, j - 1, k - 1], cid[i, j, k - 1]), F[i, j, k] >= 0)
    cross = (F[:, :-1, :] < 0) != (F[:, 1:, :] < 0)
    for (i, j, k) in np.argwhere(cross):
        if 1 <= i <= nx - 1 and 1 <= k <= nz - 1 and j <= ny - 1:
            emit((cid[i, j, k], cid[i, j, k - 1],
                  cid[i - 1, j, k - 1], cid[i - 1, j, k]), F[i, j, k] >= 0)
    cross = (F[:, :, :-1] < 0) != (F[:, :, 1:] < 0)
    for (i, j, k) in np.argwhere(cross):
        if 1 <= i <= nx - 1 and 1 <= j <= ny - 1 and k <= nz - 1:
            emit((cid[i, j, k], cid[i - 1, j, k],
                  cid[i - 1, j - 1, k], cid[i, j - 1, k]), F[i, j, k] >= 0)

    tris = np.asarray(tris, dtype=np.int64)
    # orientation settled once, by signed volume — outward is positive
    vol = np.einsum("ij,ij->i", verts[tris[:, 0]],
                    np.cross(verts[tris[:, 1]], verts[tris[:, 2]])).sum() / 6.0
    if vol < 0:
        tris = tris[:, ::-1]
    return verts, tris


def project(verts, sdf, steps=8):
    """Slide each vertex along the gradient onto sdf = 0."""
    v = verts.copy()
    eps = 1e-3
    for _ in range(steps):
        d = sdf(v)
        gr = np.zeros_like(v)
        for ax in range(3):
            o = np.zeros(3)
            o[ax] = eps
            gr[:, ax] = (sdf(v + o) - sdf(v - o)) / (2 * eps)
        gr /= np.maximum(np.linalg.norm(gr, axis=1, keepdims=True), 1e-9)
        v -= gr * d[:, None]
    return v


def neighbours(nv, tris):
    nb = [set() for _ in range(nv)]
    for (a, b, c) in tris:
        nb[a].update((b, c))
        nb[b].update((a, c))
        nb[c].update((a, b))
    return [np.fromiter(s, dtype=np.int64) for s in nb]


def relax(verts, tris, sdf, rounds=3, lam=0.5):
    """Laplacian smoothing with re-projection: the voxel grain goes without the
    limbs shrinking."""
    nb = neighbours(len(verts), tris)
    v = verts.copy()
    for _ in range(rounds):
        avg = np.stack([v[n].mean(axis=0) if len(n) else v[i]
                        for i, n in enumerate(nb)])
        v = v * (1 - lam) + avg * lam
        v = project(v, sdf, steps=3)
    return v


def vert_normals(v, tris):
    n = np.zeros_like(v)
    fn = np.cross(v[tris[:, 1]] - v[tris[:, 0]], v[tris[:, 2]] - v[tris[:, 0]])
    for i in range(3):
        np.add.at(n, tris[:, i], fn)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln == 0] = 1
    return n / ln


# ── glTF writer (unchanged contract) ─────────────────────────────────────────

def pad4(b, fill=b"\x00"):
    """glTF chunks are 4-byte aligned. The JSON chunk must be padded with
    SPACES, not nulls — a JSON parser will choke on a trailing NUL."""
    return b + fill * ((4 - len(b) % 4) % 4)


def write_glb(path, sex, base_v, base_n, tris, targets, levels):
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
        if mn is not None:
            a["min"], a["max"] = mn, mx
        accs.append(a)
        return len(accs) - 1

    def vec3(vs):
        arr = np.asarray(vs, dtype="<f4")
        return arr.tobytes(), arr.min(axis=0).tolist(), arr.max(axis=0).tolist()

    d, mn, mx = vec3(base_v)
    a_pos = add(d, 34962, 5126, "VEC3", len(base_v), mn, mx)
    d, _, _ = vec3(base_n)
    a_nrm = add(d, 34962, 5126, "VEC3", len(base_n))
    a_idx = add(np.asarray(tris, dtype="<u4").tobytes(),
                34963, 5125, "SCALAR", len(tris) * 3)

    tgt = []
    for (v, n) in targets:
        d, mn, mx = vec3(v - base_v)
        tp = add(d, 34962, 5126, "VEC3", len(v), mn, mx)
        d, _, _ = vec3(n - base_n)
        tn = add(d, 34962, 5126, "VEC3", len(n))
        tgt.append({"POSITION": tp, "NORMAL": tn})

    gltf = {
        "asset": {"version": "2.0", "generator": "opendiet/build_body_glb.py"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "body"}],
        "meshes": [{
            "name": "body",
            "weights": [0.0] * len(tgt),
            "primitives": [{
                "attributes": {"POSITION": a_pos, "NORMAL": a_nrm},
                "indices": a_idx,
                "targets": tgt
            }],
            "extras": {
                "bodyFat": levels,
                "sex": sex,
                "targetNames": ["bf%d" % b for b in levels[1:]]
            }
        }],
        "accessors": accs,
        "bufferViews": views,
        "buffers": [{"byteLength": len(buf)}]
    }

    js = pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bn = pad4(bytes(buf))
    total = 12 + 8 + len(js) + 8 + len(bn)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<III", 0x46546C67, 2, total))
        fh.write(struct.pack("<II", len(js), 0x4E4F534A))
        fh.write(js)
        fh.write(struct.pack("<II", len(bn), 0x004E4942))
        fh.write(bn)
    return total


def build(sex):
    levels = LEVELS[sex]
    span = levels[-1] - levels[0]
    t0 = time.time()

    def sdf_at(bf):
        f = (bf - levels[0]) / span
        return lambda P: sdf_body(np.atleast_2d(P), sex, f)

    base_sdf = sdf_at(levels[0])
    lo, hi = (-0.43, -0.02, -0.20), (0.43, 1.80, 0.24)
    v, tris = surface_nets(base_sdf, lo, hi, VOX)
    v = relax(v, tris, base_sdf)
    n = vert_normals(v, tris)

    # Fatter levels are reached by walking THROUGH the levels rather than
    # jumping to each from the base: every step is a small inflation, so where
    # two surfaces close on each other — an arm against a flank, a bust onto a
    # belly — the vertices are carried outward gradually instead of being torn
    # between the two sides of a gap that no longer exists.
    #
    # The arms need one more courtesy. Fat does not only inflate them, it
    # TRANSLATES them (the ao term): a sideways shift larger than the arm's own
    # radius scrambles nearest-point correspondence — inner-wall vertices land
    # on the outer wall and the tube crumples. So the known shift is applied to
    # the arm vertices first, and the projection is left with nothing to do but
    # the inflation it is good at.
    def prewarp(vv, dao):
        x, y = vv[:, 0], vv[:, 1]
        wx = np.clip((np.abs(x) - 0.13) / 0.05, 0, 1)
        wy = np.clip((y - 0.70) / 0.10, 0, 1) * np.clip((1.47 - y) / 0.12, 0, 1)
        out = vv.copy()
        out[:, 0] += np.sign(x) * dao * wx * wy
        return out

    targets = []
    cur = v
    fprev = 0.0
    for bf in levels[1:]:
        fnow = (bf - levels[0]) / span
        sdf = sdf_at(bf)
        cur = prewarp(cur, (fnow - fprev) * 0.055)
        cur = project(cur, sdf, steps=10)
        # A light touch only: a strong relax averages small features — the
        # hands — out of existence before the projection can put them back.
        cur = relax(cur, tris, sdf, rounds=1, lam=0.22)
        targets.append((cur.copy(), vert_normals(cur, tris)))
        fprev = fnow

    path = os.path.join(OUT, "body-%s.glb" % sex)
    size = write_glb(path, sex, v, n, tris, targets, levels)
    print("%s  %d verts  %d tris  %d targets  %.0f KB  %.1fs"
          % (os.path.relpath(path, HERE), len(v), len(tris),
             len(levels) - 1, size / 1024.0, time.time() - t0))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for sex in ("m", "f"):
        build(sex)
