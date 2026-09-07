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
     protein, carbohydrate, fat, fibre, sugar, energy — would exceed a band.
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

# A gram is not a gram. One of fat is nine calories, one of protein or carbohydrate is
# four, one of fibre is two and one of water is none — so a band in grams asks more of a
# fatty food than of a starchy one for no reason anybody can defend, and a floor of a gram
# and a half of carbohydrate is a tenth of a boiled potato and a fiftieth of a sausage.
# What makes two entries the same food is that the energy does not move and neither does
# where the energy comes from. So the three that carry the energy are banded by what a
# difference in them does to it, as a share of the food's own energy.
KCAL_PER_G = {"p": 4, "c": 4, "f": 9}
ENERGY_TOL = 0.15
# And under twenty calories in a hundred grams is not a difference anybody eats: it is a
# fifth of an apple, and holding a raw kale apart from a boiled one over sixteen of them
# is a strictness that serves nothing. Without this the share alone asks more of a lettuce
# than of a cheese, which is the same fault the gram floors had, upside down.
ENERGY_FLOOR = 20.0
# The rest carry meaning without much energy, and keep a band in grams: (floor, share of
# the largest value in the pool). The three fats the fat figure breaks into veto only a
# difference of kind — coconut oil against olive — never the butter in an omelet.
# Fibre's floor is the one that has to be argued for. Kale runs 2.0 to 4.1 grams across
# USDA's own entries — 2.3 in the boiled kale with salt and 4.0 in the boiled kale without,
# which is the same vegetable twice — while white bread and wholemeal run 2.7 to 7.0 and
# are two different loaves. A floor of two and a half grams sits between them with room on
# both sides.
BAND = {
    "fb": (2.5, 0.25), "sg": (1.5, 0.25), "kcal": (20, 0.25),
    "sf": (1.5, 0.35), "mo": (1.5, 0.35), "po": (1.5, 0.35),
}
AXES_G = list(BAND)
# Water is not on that list, and why it is not is the same argument the list is built on.
# A band has to be measured in what a difference costs, and water is the one figure in the
# row that is not a measurement of the food at all: it is a hundred grams minus the food.
# So a difference in water is a difference in dry matter, and what that is worth is set by
# the dry matter displaced — which protein, carbohydrate, fat and energy already band, in
# energy. Banding water as a share of itself was the last place the rule this file rejects
# survived: it asked least where water is most of the food and a gram of dry matter counts
# for most, and most where water is least and it counts for least. Backwards, and in grams.
#
# It was not a small error. Water alone refused 2,082 merges every other axis passed — more
# than any other axis on its own — and it lost the boiled chickpea from the canned one by a
# hundredth of a gram while the energy that actually separates them sat 26 kcal inside a
# band of 41. Without it the same rules speak for 89 more foods, and the families that open
# are families: pecans across roastings, pie crust baked and unbaked, ham by cut.
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
AXES = AXES_G + list(KCAL_PER_G)
MIN_MEMBERS = 2
# The figures a release does not always analyse. Where nobody measured one, SR Legacy
# leaves the nutrient out and the build writes a zero, so a zero here says two things at
# once — "none of it" and "nobody looked" — and only the parent figure tells them apart.
# Milk with five grams of carbohydrate and no sugar has not been measured: the
# carbohydrate in milk is sugar. A zero under a parent that is not zero is therefore
# unknown, and an unknown neither vetoes a merge nor drags a mean down.
PARENT = {"sg": "c", "fb": "c", "sf": "f", "mo": "f", "po": "f"}
MIN_TELLING_WORDS = 2

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


# Set from the library: True where the file promises every zero in it was measured.
MEASURED = False


def known(row, a):
    """Whether the row actually carries a figure on this axis, or only a zero standing in
    for a measurement nobody made. A library built by a tools/build_data.py that keeps the
    difference says so and is believed; an older one has to be read for the tell, which is
    a figure of zero under a parent figure that is not — milk with five grams of
    carbohydrate and no sugar was not measured, since the carbohydrate in milk is sugar."""
    v = field(row, a)
    if v is None:
        return False
    if MEASURED:
        return True
    parent = PARENT.get(a)
    return not (parent and v == 0 and field(row, parent) > 0.5)


def head_of(name):
    segs = [x.strip() for x in name.split(",")]
    if segs[0].lower() in CATEGORY_HEADS and len(segs) > 1:
        return segs[0] + ", " + segs[1]
    return segs[0]


class Pool:
    __slots__ = ("members", "lo", "hi", "seen")

    def __init__(self, i, row):
        self.members = [i]
        self.seen = {a: known(row, a) for a in AXES}
        self.lo = {a: (field(row, a) if self.seen[a] else 0.0) for a in AXES}
        self.hi = dict(self.lo)

    def fits(self, other):
        # Raw and cooked used to be a cannot-link here, because a pool of raw kale and
        # boiled kale came out named "Kale, raw". That was the name lying, not the pool
        # being wrong: a name is the segments every member has now, so such a pool is
        # called "Kale" and says exactly what it is. Where cooking does move the numbers —
        # rice, pasta, beans, a potato, any meat — the bands part them without being told
        # to; where it does not, as in a leaf that is nine tenths water either way, there
        # was never anything to part.
        energy = max(ENERGY_FLOOR,
                     ENERGY_TOL * max(self.hi["kcal"], other.hi["kcal"]))
        for a in AXES:
            # An axis votes only where both sides have something to say on it.
            if not (self.seen[a] and other.seen[a]):
                continue
            lo = min(self.lo[a], other.lo[a])
            hi = max(self.hi[a], other.hi[a])
            if a in KCAL_PER_G:
                band = energy / KCAL_PER_G[a]
            else:
                floor, share = BAND[a]
                band = max(floor, share * abs(hi))
            if hi - lo > band:
                return False
        return True

    def absorb(self, other):
        self.members += other.members
        for a in AXES:
            if not other.seen[a]:
                continue
            if not self.seen[a]:
                self.lo[a], self.hi[a], self.seen[a] = other.lo[a], other.hi[a], True
            else:
                self.lo[a] = min(self.lo[a], other.lo[a])
                self.hi[a] = max(self.hi[a], other.hi[a])


def apart(x, y):
    """How far two rows are in calories: the energy between them, and the energy moved by
    the difference in each macro that carries it."""
    return abs(field(x, "kcal") - field(y, "kcal")) + sum(
        per * abs(field(x, a) - field(y, a)) for a, per in KCAL_PER_G.items())


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
            pairs.append((-jaccard(quals[a], quals[b]), apart(ra, rb), a, b))
    # Words propose the order and numbers break its ties: "cooked, omelet" shares one word
    # with "cooked, fried" and one with "cooked, hard-boiled", and which it is put with
    # should not come down to which USDA happened to file first.
    pairs.sort()
    # Repeat until nothing more fits. A pool grows as it goes, so a merge refused early
    # can become possible later; one pass would leave a row outside a pool it belongs in,
    # and a pool that is not everything it could be is an arbitrary slice of its head.
    moved = True
    while moved:
        moved = False
        for _, _, a, b in pairs:
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
    # A segment is shared when every member has that segment, not when its words turn up
    # somewhere in every member. "Beerwurst, pork and beef" contains the word pork, but a
    # pool of it and "Beerwurst, beer salami, pork" is not a pork beerwurst — two thirds of
    # it is beef as well. What they share is the name of the sausage, and that is the name.
    shared = None
    for n in names:
        segs = {seg for seg in segs_of(n) if seg}
        shared = segs if shared is None else shared & segs
    common = None
    for n in names:
        toks = {t for seg in segs_of(n) for t in words(seg)}
        common = toks if common is None else common & toks
    # A segment survives whole where every word of it is shared. Where it is not, the
    # run of words it opens with can still be shared and still be a phrase — "with added
    # nonfat milk solids" out of "…solids and vitamin A and vitamin D" — and that phrase
    # names the family better than dropping the segment does. It has to end on a word
    # that carries a food, or the name trails off mid-breath.
    order, partial = [], False
    for seg in segs_of(names[0]):
        toks = words(seg)
        if not seg or not toks:
            continue
        if seg in shared:
            order.append(seg)
            continue
        raw = [w for w in re.split(r"[^A-Za-z0-9%]+", seg) if w]
        keep = []
        for w in raw:
            if stem(w.lower()) not in common:
                break
            keep.append(w)
        while keep and (stem(keep[-1].lower()) in EMPTY or len(keep[-1]) < 2):
            keep.pop()
        # One such phrase per name: a second is a name assembled out of scraps.
        if len(keep) >= MIN_TELLING_WORDS and not partial:
            order.append(" ".join(keep))
            partial = True
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


def pool_row(p, foods):
    members = sorted(p.members)
    rows = [foods[i] for i in members]
    names = [r[IX["name"]] for r in rows]
    name = shared_name(names)
    out = [None] * 18
    out[IX["name"]] = name
    out[IX["cat"]] = rows[0][IX["cat"]]
    for k in MEANED:
        vals = [field(r, k) for r in rows if known(r, k)]
        out[IX[k]] = round(sum(vals) / len(vals), 2 if k != "kcal" else 0) if vals else 0
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


MAX_TELLING = 3
# Words that carry no food in them: they cannot be what tells two pools apart.
EMPTY = {"with", "without", "and", "or", "in", "of", "the", "a", "an", "to", "from",
         "added", "includes", "all", "extra", "style", "type", "prepared", "made",
         "including", "plus", "not", "no", "unspecified", "other", "regular", "commercial",
         "commercially", "home", "each", "per", "used", "use", "uses", "for", "on", "at",
         "by", "is", "as", "its", "than", "this", "that", "these", "those", "only", "both"}


def member_words(r, foods, every=False):
    """The words the pool's members use after the head: any of them, or — with every —
    only the words all of them use. A name may only be told by the second kind. Half the
    members being frozen does not make the pool frozen, and a name that says so of the
    other half is a name that is not true."""
    out = None if every else set()
    for i in r[MEMBERS]:
        n = foods[i][IX["name"]]
        depth = head_of(n).count(",") + 1
        toks = {t for seg in [x.strip() for x in n.split(",")][depth:] for t in words(seg)}
        if every:
            out = toks if out is None else out & toks
        else:
            out |= toks
    return out or set()


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
        all_own = {id(r): member_words(r, foods, every=True) for r in group}
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
            telling = sorted(w for w in all_own[id(r)] - others if w not in EMPTY and len(w) > 1)
            if telling and len(telling) <= MAX_TELLING:
                r[IX["name"]] = name + ", " + " or ".join(telling)
    return rows


def drop_twins(rows, foods):
    """A pool named exactly what one of its members is named is not a row anyone can read:
    two lines of the same words, and the reader has to guess which one they meant. It
    happens where USDA already ships the generic entry the varieties are variations on —
    "Apples, raw, with skin" beside five named apples, "Beerwurst, pork and beef" beside
    the beer salami. That generic already is the average of the family, written by somebody
    who measured it, so the pool has nothing to add and goes. Its members stay where they
    are."""
    keep = []
    for r in rows:
        names = {foods[i][IX["name"]] for i in r[MEMBERS]}
        if r[IX["name"]] not in names:
            keep.append(r)
    return keep



def drop_clashes(rows, foods):
    """Two pools under one head whose members share the same words come out with the same
    name, and a name that is not the name of one thing is not a name: the plate keys on it,
    and a reader cannot pick between two rows that read alike. They used to be told apart by
    the figure they were furthest apart on — "Apricots \u00b7 carbs 22 g" — which put a
    nutrient in the middle of a food's name and answered a question nobody had asked.

    So the larger pool keeps the name and the rest do not get one. Nothing leaves the
    library: their entries were always in it, and they go back to standing on their own,
    which is what an entry that cannot be spoken for does."""
    seen = defaultdict(list)
    for r in rows:
        seen[r[IX["name"]].lower()].append(r)
    keep = set()
    for group in seen.values():
        # Size decides, and where two are the same size the earlier member does, so the
        # same library always yields the same pools.
        best = sorted(group, key=lambda r: (-len(r[MEMBERS]), r[MEMBERS][0]))[0]
        keep.add(id(best))
    return [r for r in rows if id(r) in keep]


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
    global MEASURED
    MEASURED = d.get("zeros") == "measured"
    pools = build_pools(foods)
    rows = [pool_row(p, foods) for p in pools]
    rows = label(drop_clashes(drop_twins(retell(rows, foods), foods), foods))
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
