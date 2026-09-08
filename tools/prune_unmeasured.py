#!/usr/bin/env python3
"""Take out of a library every food carrying a figure nobody measured.

FDC writes a row for a nutrient somebody analysed and no row at all for one nobody did,
and the build used to read both as 0.0 — see data/README.md. tools/build_data.py keeps the
difference now, but the libraries in data/ were built before it did, so the difference is
already gone from them and the file has to be asked instead of the source.

It can answer. A zero is only suspicious where its neighbours say it should not happen, so
the rule is drawn from the file rather than from anybody's idea of food: within a category,
among the foods that have the parent figure, count how many report the figure itself. Where
most of them do, a zero is the odd one out and the food goes. Where most of them do not, a
zero is what that category looks like and the food stays.

That is what parts milk from kale. Four dairy foods in five carry carbohydrate and no
fibre, because milk has no fibre — so a zero there is a measurement, and milk stays. Nine
vegetables in ten carry fibre, so a vegetable with carbohydrate and none is a vegetable
nobody tested, and it goes. Sugar goes the same way and reaches further: outside meat and
seafood, a food with carbohydrate almost always reports some, and the ones that report a
little report 0.2, 0.4, 0.9 — hardly any land in the sliver just above zero. A figure with
that shape has no true zeros to speak of, so the zeros in it are gaps.

Two more, which need no counting:

  · fat over a gram is made of saturated, mono and poly fat. Four zeros under it are four
    measurements nobody took, whatever the category does.
  · and a food whose own figures contradict each other is not to be trusted either —
    tools/audit_data.py asks that, and what it finds goes out with the rest.

The category rule reaches too far for a food that has no room left for the figure it is
short of. A category vote is only a proxy for "does this kind of food usually carry the
figure" — but a food that is almost nothing but sugar has no carbohydrate left over for
fibre to hide in, whatever SWEETS or BAKED usually do, so a fibre zero there is read
alongside the food's own sugar rather than its neighbours':

  · **fibre zero is measured when sugar already accounts for the carbohydrate** — sugar at
    or above 85% of carbohydrate leaves too little else for fibre to be a plausible gap.
    Granulated, brown and powdered sugar (97-99.8% of their carb is reported as sugar),
    maple syrup (90%) and vanilla extract (100%) clear this; cider vinegar (44%) and baking
    powder (0%, its carbohydrate is starch and bicarbonate, not sugar) do not, because for
    them the missing figure is not explained by sugar at all.
  · **a keep-list for the handful the numbers cannot rule on**: cornstarch and baking
    powder report zero sugar in categories (GRAINS, BAKED) where most foods carry some —
    correctly, since neither is made of anything sugar comes from — and cider and balsamic
    vinegar report zero fibre for the same reason vinegar has none to report. No rule drawn
    from the file tells these apart from a food nobody measured; a name each, looked at once
    and written here, does.

The pools go too: they are indices into the list this rewrites, and tools/pool_foods.py
rebuilds them afterwards. Once a library has been through this, every zero left in it is a
figure somebody wrote down, which the file then says — "zeros": "measured" — and the
pooling stops guessing at it.

    python3 tools/prune_unmeasured.py             # rewrite data/*.json in place
    python3 tools/prune_unmeasured.py --dry-run   # say what would go, change nothing
    python3 tools/prune_unmeasured.py --why       # print the rule each category got
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_data import IX, check, get           # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# A figure that can be missing, and the figure that says whether a zero under it is real.
PARENT = {"sg": "c", "fb": "c"}
FLOOR = 0.5
# Where this share of a category's foods carry the figure, a zero in it is the odd one out.
NORM = 0.6
# The fat breakdown needs no category to judge it: a fat is made of fatty acids.
FAT_PARTS = ("sf", "mo", "po", "tr")
FAT_FLOOR = 1.0
# Sugar at or above this share of carbohydrate leaves too little else for a fibre zero to
# be a plausible gap; see the docstring.
SUGAR_FRACTION = 0.85
# Exact names the numbers cannot rule on either way — looked at once, kept regardless of
# what the category vote or the sugar share says.
KEEP = frozenset({
    "Cornstarch",
    "Leavening agents, baking powder, double-acting, sodium aluminum sulfate",
    "Leavening agents, baking powder, double-acting, straight phosphate",
    "Leavening agents, baking powder, low-sodium",
    "Vinegar, balsamic",
    "Vinegar, cider",
})


def expected(foods):
    """{(figure, category): whether a zero there is a gap}, counted off the file."""
    seen = defaultdict(lambda: [0, 0])
    for r in foods:
        cat = get(r, "cat")
        for k, parent in PARENT.items():
            if get(r, parent) > FLOOR:
                seen[(k, cat)][0] += 1
                seen[(k, cat)][1] += get(r, k) != 0
    return {key: (n and got / n >= NORM) for key, (n, got) in seen.items()}, seen


def unmeasured(row, rule):
    """Why this row should go, or None."""
    if get(row, "name") in KEEP:
        return None
    why = []
    for k, parent in PARENT.items():
        if get(row, parent) <= FLOOR or get(row, k) != 0:
            continue
        if k == "fb" and get(row, "sg") >= SUGAR_FRACTION * get(row, parent):
            continue
        if rule.get((k, get(row, "cat"))):
            why.append(k)
    if get(row, "f") > FAT_FLOOR and not any(get(row, k) for k in FAT_PARTS):
        why.append("fat breakdown")
    return "no " + ", ".join(why) + " figure" if why else None


def prune(foods):
    """Returns the foods to keep, the ones to drop with a reason, and the rule per category."""
    rule, counts = expected(foods)
    faults, _ = check(foods)
    contradicted = {}
    for fault, hits in faults:
        for _, name in hits:
            contradicted.setdefault(name, fault)
    keep, gone = [], []
    for r in foods:
        name = r[IX["name"]]
        why = unmeasured(r, rule) or contradicted.get(name)
        (gone.append((name, why)) if why else keep.append(r))
    return keep, gone, rule, counts


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lib", action="append", help="a library to prune; repeatable")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--why", action="store_true", help="print the rule each category got")
    ap.add_argument("--show", type=int, default=8)
    args = ap.parse_args()
    libs = args.lib or ["core", "legacy", "survey"]

    for lib in libs:
        path = ROOT / "data" / f"{lib}.json"
        d = json.loads(path.read_text())
        cats = d["cats"]
        before = len(d["foods"])
        keep, gone, rule, counts = prune(d["foods"])
        print(f"{lib}: {before} foods, {len(gone)} out for want of a measurement, "
              f"{len(keep)} left")
        if args.why:
            for k in PARENT:
                for ci, cat in enumerate(cats):
                    n, got = counts.get((k, ci), (0, 0))
                    if n < 20:
                        continue
                    verdict = "a zero is a gap" if rule[(k, ci)] else "a zero is a figure"
                    print(f"      {k:3} {cat:8} {got:5}/{n:<5} carry it  ->  {verdict}")
        for name, why in gone[:args.show]:
            print(f"      {name[:58]:60} {why}")
        if len(gone) > args.show:
            print(f"      … {len(gone) - args.show} more")
        if args.dry_run:
            continue
        d["foods"] = keep
        # Every zero left is one somebody measured, and the file can say so now.
        d["zeros"] = "measured"
        # The pools index into the list this just rewrote. tools/pool_foods.py rebuilds them.
        d.pop("pools", None)
        path.write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False) + "\n")
        print(f"      wrote {path}")


if __name__ == "__main__":
    main()
