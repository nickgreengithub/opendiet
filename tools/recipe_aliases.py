#!/usr/bin/env python3
"""Check data/aliases.json against the real matcher, or suggest candidates for new phrases.

An alias is a claim: "this phrase means that food" (pin), or "this phrase should search for
that" (q). Neither claim can be checked by reading the JSON — only by asking recipe.js, the
same code the app runs, which is why this shells out to node rather than reimplementing
rankFoods here. The two must never drift, so there is no second scorer in this file.

    python3 tools/recipe_aliases.py --check              # every alias against every library
    python3 tools/recipe_aliases.py --check --lib legacy
    python3 tools/recipe_aliases.py --suggest phrases.txt # nearest library names per phrase,
                                                           # for a human to review and paste
                                                           # rows back — no API call here
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECIPE_JS = ROOT / "recipe.js"


def run_node(script):
    p = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr, file=sys.stderr)
        sys.exit(1)
    return json.loads(p.stdout)


def check(lib):
    # Runs matchLine itself — the same code the app calls — rather than reimplementing its
    # scoring here. `weak` on the result means the alias's own q/pin found nothing and
    # matchLine fell back to the bare head noun, which a raw rankFoods count alone would
    # miss (the fallback can still turn up a food, just not the one the alias asked for).
    aliases_path = ROOT / "data" / "aliases.json"
    lib_path = ROOT / "data" / f"{lib}.json"
    script = f"""
const OD = require({json.dumps(str(RECIPE_JS))});
const fs = require("fs");
const d = JSON.parse(fs.readFileSync({json.dumps(str(lib_path))}, "utf8"));
const foods = OD.mkFoods(d);
const aliases = JSON.parse(fs.readFileSync({json.dumps(str(aliases_path))}, "utf8"));
const out = [];
for (const alias of aliases) {{
  const phrase = alias.m[0];
  const line = {{ ing: phrase, prep: [], state: alias.state || null }};
  const m = OD.matchLine(line, foods, aliases);
  out.push({{
    phrase, pin: alias.pin || null, food: m.food, cands: m.cands.slice(0, 5), weak: m.weak,
  }});
}}
console.log(JSON.stringify(out));
"""
    return run_node(script)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--lib", default="legacy")
    ap.add_argument("--suggest", metavar="FILE")
    args = ap.parse_args()

    if args.check:
        results = check(args.lib)
        bad = 0
        for r in results:
            if r["food"] is None:
                print(f"  NO MATCH   {r['phrase']!r:35}")
                bad += 1
            elif r["weak"]:
                print(f"  WEAK       {r['phrase']!r:35} q/pin found nothing, fell back to head noun; got {r['food']!r}")
                bad += 1
            elif r["pin"] and r["food"] != r["pin"]:
                print(f"  #1 != pin  {r['phrase']!r:35} got {r['food']!r}, wanted {r['pin']!r}")
                print(f"             top candidates: {r['cands']}")
                bad += 1
        print(f"\n{len(results)} aliases checked against {args.lib}, {bad} need attention")
        sys.exit(1 if bad else 0)

    if args.suggest:
        phrases = [l.strip() for l in Path(args.suggest).read_text().splitlines() if l.strip()]
        lib_path = ROOT / "data" / f"{args.lib}.json"
        script = f"""
const OD = require({json.dumps(str(RECIPE_JS))});
const fs = require("fs");
const d = JSON.parse(fs.readFileSync({json.dumps(str(lib_path))}, "utf8"));
const foods = OD.mkFoods(d);
const phrases = {json.dumps(phrases)};
const out = phrases.map(p => {{
  const ranked = OD.rankFoods(foods.slice(), p.toLowerCase());
  ranked.sort((a, b) => b._hit - a._hit);
  return {{ phrase: p, near: ranked.slice(0, 15).map(f => f.name) }};
}});
console.log(JSON.stringify(out));
"""
        for row in run_node(script):
            print(f"\n{row['phrase']}:")
            for name in row["near"]:
                print(f"  {name}")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
