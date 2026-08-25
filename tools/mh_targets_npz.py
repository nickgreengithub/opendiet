"""Compact MakeHuman's 1,280 .target text files into the single npz the bake
reads.

The inputs are not vendored — they are MakeHuman's own data, released CC0 in
2020, and they live in the MakeHuman repository:

    git clone --depth 1 https://github.com/makehumancommunity/makehuman.git
    python3 tools/mh_targets_npz.py makehuman <dir>/targets.npz
    cp makehuman/makehuman/data/3dobjs/base.obj        <dir>/mh_base.obj
    cp makehuman/makehuman/data/rigs/default.mhskel    <dir>/mh_default.mhskel
    cp makehuman/makehuman/data/rigs/default_weights.mhw <dir>/mh_default_weights.mhw
    python3 tools/makehuman_bake.py <dir>

Note the pypi package carries the code and not the assets, and the project's
own asset host is a separate download.

Each target is a sparse list of vertex deltas; the archive keeps them as an
index array and an int16 vector in thousandths, which is how MakeHuman's own
algos3d stores them."""
import os, sys, numpy as np
root = sys.argv[1]
out = sys.argv[2]
tdir = os.path.join(root, "makehuman", "data", "targets")
data = {}
n = 0
for dirpath, _, files in os.walk(tdir):
    for f in files:
        if not f.endswith(".target"):
            continue
        p = os.path.join(dirpath, f)
        rel = os.path.relpath(p, tdir)[:-len(".target")].replace(os.sep, "/")
        idx, vec = [], []
        for line in open(p, encoding="latin-1"):
            line = line.strip()
            if not line or line[0] == "#":
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            idx.append(int(parts[0]))
            vec.append([float(parts[1]), float(parts[2]), float(parts[3])])
        # A few targets are all comment and no deltas — the "average"
        # reference of each macro axis is the identity. They still need a key,
        # or the composer that asks for them by name falls over.
        data["targets/%s.index" % rel] = np.array(idx, dtype=np.int32)
        data["targets/%s.vector" % rel] = (np.round(
            np.array(vec, dtype=np.float64) * 1000.0).astype(np.int16)
            if vec else np.zeros((0, 3), dtype=np.int16))
        n += 1
np.savez_compressed(out, **data)
print("%d targets -> %s (%.1f MB)" % (n, out, os.path.getsize(out) / 1e6))
