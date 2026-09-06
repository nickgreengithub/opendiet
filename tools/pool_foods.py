#!/usr/bin/env python3
"""Pool the near-identical entries in a library into one typical row each.

A search for a plain word returns dozens of USDA entries that differ in name and
hardly at all in the numbers — bread by the bakery, milk by the vitamin added, ham by
the packing. This finds those families and writes one extra row per family: the
mean of its members, named by the words they all share, carrying the list of what
went into it. Nothing is removed. The originals stay for anyone who meant one of
them; the pool ranks first for anyone who did not.

    python3 tools/pool_foods.py               # rewrite data/legacy.json in place
    python3 tools/pool_foods.py --dry-run     # print the pools and stop
    python3 tools/pool_foods.py --lib survey  # another library

How a pool is found — constrained agglomerative clustering, in three parts:

  1. Words propose. Entries are grouped by the head of the name (before the first
     comma), and within a head every pair is scored by how many qualifier words
     they share. Pairs are merged most-similar first.

  2. Numbers veto. A merge is refused if the merged pool's range on ANY axis —
     protein, carbohydrate, fat, fibre, sugar, water, energy — would exceed a band.
     The band is on the pool's diameter rather than on the pair, so a pool cannot
     grow by chaining: every member of a finished pool is within the band of every
     other member, which is what makes the mean representative of all of them.
     The band is the larger of an absolute floor and a share of the value, so it
     is one gram of fat for milk and eight for butter. Category and liquid/solid
     are hard cannot-links.

  3. The head is the only text requirement. "Bread, rye" and "Bread, oatmeal"
     share nothing but the head; if the numbers agree they pool as "Bread", which
     is what a search for bread wants. "Bread, white" and "Bread, whole-wheat"
     part on fibre. "Milk, whole" and "Milk, nonfat" part on fat. Nobody has to
     say which qualifiers matter — the numbers do.

Brands are left out: a "KFC" pool would be typical of nothing anyone shops for.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Same rules index.html uses, so a brand here is a brand there.
BRANDED = re.compile(r"\b(?!NFS\b|NS\b|USDA\b|RTE\b|UPC\b|I{2,3}\b|IV\b)[A-Z]{2,}\b")
OWNED = re.compile(r"\b[A-Z][a-z]+'s\b")

# The band per axis: (absolute floor, share of the largest value in the pool).
# The pool's range on the axis must stay within max(floor, share * max).
BAND = {
    "p": (0.8, 0.25), "c": (1.5, 0.25), "f": (0.8, 0.25),
    "fb": (0.8, 0.25), "sg": (1.5, 0.25), "wa": (2.0, 0.06), "kcal": (12, 0.25),
    # The three fats the fat figure breaks into are a detail of a detail: they veto only
    # a difference that is a difference of kind — coconut oil against olive — never the
    # butter in an omelet. A tight band here was what kept a scrambled egg from pooling
    # with a boiled one.
    "sf": (1.5, 0.35), "mo": (1.5, 0.35), "po": (1.5, 0.35),
}
# USDA files some things under a category rather than a food — "Beverages, coffee",
# "Snacks, potato chips", "Fast foods, hamburger". For these the head is the first two
# segments, or every drink in the book would pool as "Beverages".
CATEGORY_HEADS = {
    "beverages", "alcoholic beverage", "snacks", "fast foods", "babyfood", "cereals",
    "cereals ready-to-eat", "soup", "sauce", "candies", "cookies", "crackers", "restaurant",
    "school lunch", "spices", "frozen novelties", "leavening agents", "seeds", "nuts",
    "infant formula", "meal", "seaweed", "syrups", "toppings", "puddings", "gravy",
    "salad dressing", "sweeteners", "desserts", "pie", "cake", "muffins", "rolls",
    "bagels", "biscuits", "pancakes", "waffles", "game meat", "sausage", "fish", "mollusks",
    "crustaceans", "cheese", "yogurt", "milk", "egg", "juice", "beans", "peas", "rice",
    # USDA files a meat as species, cut, treatment — "Beef, chuck, ...", "Pork, loin, ...".
    # Under the species alone a pool spans cuts that have nothing to do with each other
    # but a fat figure, so for these the cut is part of the head.
    "beef", "pork", "lamb", "veal", "chicken", "turkey", "duck", "goose", "ostrich",
    "emu", "bison", "buffalo", "elk", "deer", "moose", "rabbit", "quail", "pheasant",
    "pasta", "noodles", "potatoes", "squash", "lettuce", "cabbage", "onions", "peppers",
    "tomatoes", "apples", "oranges", "grapes", "berries", "oil", "margarine", "butter",
}
AXES = list(BAND)
MIN_MEMBERS = 2

# Field layout of a food row — see data/README.md.
IX = {"name": 0, "cat": 1, "kcal": 2, "p": 3, "c": 4, "fb": 5, "f": 6, "sf": 7, "sg": 8,
      "ml": 9, "cm": 10, "pg": 11, "pn": 12, "wa": 13, "ah": 14, "mo": 15, "po": 16, "al": 17}
MEANED = ["kcal", "p", "c", "fb", "f", "sf", "sg", "wa", "ah", "mo", "po", "al"]
MEMBERS = 19      # after the 18 food fields and trans fat
ALIASES = 20


def stem(w):
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w[-3:] in ("oes", "ses", "xes", "hes"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def words(text):
    return [stem(w) for w in re.split(r"[^a-z0-9%]+", text.lower()) if w]


def field(row, k):
    i = IX[k]
    return row[i] if i < len(row) else 0


def head_of(name):
    segs = [x.strip() for x in name.split(",")]
    if segs[0].lower() in CATEGORY_HEADS and len(segs) > 1:
        return segs[0] + ", " + segs[1]
    return segs[0]


class Pool:
    __slots__ = ("members", "lo", "hi")

    def __init__(self, i, row):
        self.members = [i]
        self.lo = {a: field(row, a) for a in AXES}
        self.hi = dict(self.lo)

    def fits(self, other):
        for a in AXES:
            lo = min(self.lo[a], other.lo[a])
            hi = max(self.hi[a], other.hi[a])
            floor, share = BAND[a]
            if hi - lo > max(floor, share * abs(hi)):
                return False
        return True

    def absorb(self, other):
        self.members += other.members
        for a in AXES:
            self.lo[a] = min(self.lo[a], other.lo[a])
            self.hi[a] = max(self.hi[a], other.hi[a])


def jaccard(a, b):
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster_head(rows):
    """rows: list of (index, row). Returns a list of Pools."""
    quals = {}
    for i, row in rows:
        name = row[IX["name"]]
        rest = name.split(",", 1)[1] if "," in name else ""
        quals[i] = frozenset(words(rest))
    pools = {i: Pool(i, row) for i, row in rows}
    owner = {i: i for i, _ in rows}

    def find(i):
        while owner[i] != i:
            owner[i] = owner[owner[i]]
            i = owner[i]
        return i

    pairs = []
    ids = [i for i, _ in rows]
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            a, b = ids[x], ids[y]
            ra, rb = rows[x][1], rows[y][1]
            if field(ra, "cat") != field(rb, "cat") or bool(field(ra, "ml")) != bool(field(rb, "ml")):
                continue
            pairs.append((-jaccard(quals[a], quals[b]), a, b))
    pairs.sort()
    # Repeat until nothing more fits. A pool grows as it goes, so a merge refused early
    # can become possible later; one pass would leave a row outside a pool it belongs in,
    # and a pool that is not everything it could be is an arbitrary slice of its head.
    moved = True
    while moved:
        moved = False
        for _, a, b in pairs:
            ra, rb = find(a), find(b)
            if ra == rb:
                continue
            if pools[ra].fits(pools[rb]):
                pools[ra].absorb(pools[rb])
                owner[rb] = ra
                del pools[rb]
                moved = True
    return list(pools.values())


def shared_name(names):
    """The words every member has, in the first member's order, after the head."""
    head = head_of(names[0])
    depth = head.count(",") + 1
    segs_of = lambda n: [x.strip() for x in n.split(",")][depth:]
    common = None
    for n in names:
        toks = {t for seg in segs_of(n) for t in words(seg)}
        common = toks if common is None else common & toks
    # A segment survives whole or not at all: a trimmed segment is prose nobody wrote.
    order = [seg for seg in segs_of(names[0])
             if seg and words(seg) and all(t in common for t in words(seg))]
    return head if not order else head + ", " + ", ".join(order)


def build_pools(foods):
    by_head = defaultdict(list)
    for i, row in enumerate(foods):
        name = row[IX["name"]]
        if BRANDED.search(name) or OWNED.search(name):
            continue
        by_head[head_of(name).lower()].append((i, row))
    pools = []
    for head, rows in by_head.items():
        if len(rows) < MIN_MEMBERS:
            continue
        pools += [p for p in cluster_head(rows) if len(p.members) >= MIN_MEMBERS]
    return pools


def _band(p, a):
    floor, share = BAND[a]
    return max(floor, share * abs(p.hi[a]))


def _gap(p, row, a):
    v = field(row, a)
    return max(0.0, p.lo[a] - v, v - p.hi[a])


def pool_row(p, foods):
    members = sorted(p.members)
    rows = [foods[i] for i in members]
    names = [r[IX["name"]] for r in rows]
    name = shared_name(names)
    out = [None] * 18
    out[IX["name"]] = name
    out[IX["cat"]] = rows[0][IX["cat"]]
    for k in MEANED:
        vals = [field(r, k) for r in rows]
        out[IX[k]] = round(sum(vals) / len(vals), 2 if k != "kcal" else 0)
    out[IX["kcal"]] = int(out[IX["kcal"]])
    liquid = 1 if field(rows[0], "ml") else 0
    out[IX["ml"]] = liquid
    out[IX["cm"]] = 0
    # No household measure belongs to a family; the fallback conversion the data
    # already uses for the rest — see tools/add_portions.py.
    out[IX["pg"]], out[IX["pn"]] = (240, "CUP") if liquid else (28.35, "OUNCES")
    # Index 18 is trans fat in a food row, so the members come after it. Then the words
    # every member shares that the name does not show — "ham" under "Pork, cured" —
    # so a search for the word still finds the pool.
    shown = set(words(name))
    common = None
    for n in names:
        toks = set(words(n))
        common = toks if common is None else common & toks
    aliases = sorted(w for w in (common or set()) if w not in shown)
    return out + [0, members, aliases]


AXIS_LABEL = {"p": "protein", "c": "carbs", "f": "fat", "fb": "fibre", "sg": "sugar",
              "wa": "water", "kcal": "kcal", "sf": "sat fat", "mo": "mono", "po": "poly"}
MAX_TELLING = 3
# Words that carry no food in them: they cannot be what tells two pools apart.
EMPTY = {"with", "without", "and", "or", "in", "of", "the", "a", "an", "to", "from",
         "added", "includes", "all", "extra", "style", "type", "prepared", "made",
         "including", "plus", "not", "no", "unspecified", "other", "regular", "commercial",
         "commercially", "home", "each", "per", "used", "use", "uses", "for", "on", "at",
         "by", "is", "as", "its", "than", "this", "that", "these", "those", "only", "both"}


def member_words(r, foods):
    """Every word the pool's members use, after the head."""
    out = set()
    for i in r[MEMBERS]:
        n = foods[i][IX["name"]]
        depth = head_of(n).count(",") + 1
        for seg in [x.strip() for x in n.split(",")][depth:]:
            out |= set(words(seg))
    return out


def retell(rows, foods):
    """A pool named "Egg, whole, cooked" sat beside one named "Egg, whole" that held the
    hard-boiled and the poached: "cooked" was not what told them apart, so the pair read
    as a food and a subset of itself. Where one pool's name nests inside another's under
    the same head and every qualifier it adds is one the sibling's members own too, the
    words only this pool's members use are added — omelet, scrambled. Names that already
    distinguish are left alone: a name has to say what the food is, not only how it
    differs."""
    by_head = defaultdict(list)
    for r in rows:
        by_head[head_of(r[IX["name"]]).lower()].append(r)
    for head, group in by_head.items():
        if len(group) < 2:
            continue
        own = {id(r): member_words(r, foods) for r in group}
        names = {id(r): r[IX["name"]] for r in group}
        for r in group:
            name = names[id(r)]
            if not any(o is not r and (name.startswith(names[id(o)] + ",")
                                       or names[id(o)].startswith(name + ",")
                                       or names[id(o)] == name) for o in group):
                continue
            others = set()
            for o in group:
                if o is not r:
                    others |= own[id(o)]
            depth = head_of(name).count(",") + 1
            segs = [x.strip() for x in name.split(",")]
            if any(seg and not all(w in others for w in words(seg)) for seg in segs[depth:]):
                continue      # the name already says something the sibling cannot
            telling = sorted(w for w in own[id(r)] - others if w not in EMPTY and len(w) > 1)
            if telling and len(telling) <= MAX_TELLING:
                r[IX["name"]] = name + ", " + " or ".join(telling)
    return rows


def dedupe_names(rows, foods):
    """White breads and wholemeal breads can come out as one name: every word they share
    is the same word. What differs is a number, so the number breaks the clash — the axis
    on which the clashing pools are furthest apart, stated for each."""
    seen = defaultdict(list)
    for r in rows:
        seen[r[IX["name"]].lower()].append(r)
    for name, group in seen.items():
        if len(group) < 2:
            continue
        best, best_axis = -1, None
        for a in AXES:
            vals = [field(r, a) for r in group]
            floor, share = BAND[a]
            spread = (max(vals) - min(vals)) / max(floor, share * max(abs(v) for v in vals) or floor)
            if spread > best:
                best, best_axis = spread, a
        unit = "" if best_axis == "kcal" else " g"
        for r in group:
            v = field(r, best_axis)
            shown = f"{v:.0f}" if best_axis == "kcal" or v >= 10 else f"{v:.1f}"
            r[IX["name"]] = f"{r[IX['name']]} \u00b7 {AXIS_LABEL[best_axis]} {shown}{unit}"
    return rows


def label(rows):
    """"Cheese, cheddar" is both a pool and a real food, and a plate cannot hold two
    things by one name. The mark goes into the name itself, since the name is what
    travels — to the plate, to the clipboard, to a saved list. The table shows it as a
    badge instead of reading it out."""
    for r in rows:
        r[IX["name"]] = f"{r[IX['name']]} \u00b7 avg"
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", default="legacy")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=25, help="pools to print, largest first")
    args = ap.parse_args()
    path = ROOT / "data" / f"{args.lib}.json"
    d = json.loads(path.read_text())
    foods = d["foods"]
    pools = build_pools(foods)
    rows = label(dedupe_names(retell([pool_row(p, foods) for p in pools], foods), foods))
    rows.sort(key=lambda r: (-len(r[MEMBERS]), r[IX["name"]]))

    sizes = [len(r[MEMBERS]) for r in rows]
    covered = sum(sizes)
    print(f"{args.lib}: {len(foods)} foods, {len(rows)} pools covering {covered} entries "
          f"({100 * covered // len(foods)}%); median size {sorted(sizes)[len(sizes) // 2]}, "
          f"largest {max(sizes)}", file=sys.stderr)
    for r in rows[:args.show]:
        print(f"  {len(r[MEMBERS]):>3}  {r[IX['name']]}", file=sys.stderr)
        for i in r[MEMBERS][:4]:
            print(f"        · {foods[i][IX['name']][:78]}", file=sys.stderr)
        if len(r[MEMBERS]) > 4:
            print(f"        · … {len(r[MEMBERS]) - 4} more", file=sys.stderr)
    if args.dry_run:
        return
    d["pools"] = rows
    path.write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"wrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
