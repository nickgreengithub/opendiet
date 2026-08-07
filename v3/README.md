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
- Everyday foods carry a cyan dot and are floated to the top of a search. The flag lives in
  the data as an eleventh element on each food row, written by `tools/mark_common.py`; the
  root site ignores it.

The food libraries are **not** copied into this folder. `index.html` reads them from the
site root via `const DATA = "../data/"`, so the two versions can never drift apart.

Promoting v3 to the root means moving these files up and setting `DATA` back to `"data/"`.
