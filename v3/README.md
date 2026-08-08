# v0.3 preview

Served at **opendiet.org/v3/**. A copy of the live site, used to try changes without
touching the version at the root. It is `noindex`, carries no social cards, and nothing
links to it.

What is different from the root:

- A launcher screen: the site is a set of small apps rather than one page. FOOD SEARCH is
  the built one; CALORIE CALC, RECIPE BUILDER and FOOD COMPARE are placeholders.
- Desktop switches app with tabs across the top. Mobile gets a back button to the launcher.
- Both layouts open on the search line alone, centred, and lift it to the header on the first
  keystroke.
- No CORE library. The everyday-food problem is solved in the search order rather than by
  filtering the data, so a long result list costs nothing. SR Legacy is the default; FNDDS
  is the other option. `data/core.json` stays for the root site, which still opens on it.
- Search matches every word of the query, in any order, anywhere in the name. Results are
  then scored — 4 for a whole word, 2 for the start of a longer one, 1 for a hit buried
  inside one, +2 for being on the everyday list, +1 for the name opening with the query —
  and ordered by that, then by the shorter name, then alphabetically. Nothing about it is
  visible: no badge, no dot.
- The everyday flag is an eleventh element on each food row, written by
  `tools/mark_common.py`; the root site reads ten and ignores it.

The food libraries are **not** copied into this folder. `index.html` reads them from the
site root via `const DATA = "../data/"`, so the two versions can never drift apart.

Promoting v3 to the root means moving these files up and setting `DATA` back to `"data/"`.
