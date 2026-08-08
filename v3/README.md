# v0.3 preview

Served at **opendiet.org/v3/**. A copy of the live site, used to try changes without
touching the version at the root. It is `noindex`, carries no social cards, and nothing
links to it.

What is different from the root:

- A launcher screen: the site is a set of small apps rather than one page. FOOD SEARCH is
  the built one; CALORIE CALC, RECIPE BUILDER and FOOD COMPARE are placeholders.
- Desktop switches app with tabs across the top. Mobile gets a back button to the launcher.
- Both layouts open on the search line alone, centred, and lift it to the header on the first
  keystroke. Reaching for the search box, or typing a different query, returns the list to
  the top; a food added on mobile slides into the summary out of a cyan wash, and the
  summary scrolls to meet it.
- No CORE library. The everyday-food problem is solved in the search order rather than by
  filtering the data, so a long result list costs nothing. SR Legacy is the default; FNDDS
  is the other option. `data/core.json` stays for the root site, which still opens on it.
- Search matches every word of the query, in any order, and treats a plural as its
  singular in both directions — "apple" finds `Apples, raw`, "eggs" finds `Egg, whole, raw`,
  "berry" reaches `Blueberries`. Results are then scored by how the query landed: 20 for a
  whole word, 12 for the start of a longer one, 4 for a hit buried inside one. Those tiers
  are further apart than every bonus put together, so nothing outranks a better match.
  Bonuses only settle foods that landed the same way: 3 for the everyday list, 1 for opening
  the name, up to 3 for landing in the name's first words, up to 3 for how much of the word
  the query spelled. Ties go to the shorter name, then the alphabet. Nothing about it is
  visible: no badge, no dot.
- The everyday flag is an eleventh element on each food row, written by
  `tools/mark_common.py`; the root site reads ten and ignores it.
- Opening a food on mobile shows the amount two ways: grams, and the same amount as
  household servings ("1 MEDIUM", "1 SLICE", "1 TBSP"). Whichever side you tap takes the
  − and + — grams move in tens, servings in whole servings — the macros follow, and ADD,
  on the same line, puts that amount on the plate. `tools/add_portions.py` writes the
  serving onto the food row as a twelfth and thirteenth element.

The food libraries are **not** copied into this folder. `index.html` reads them from the
site root via `const DATA = "../data/"`, so the two versions can never drift apart.

Promoting v3 to the root means moving these files up and setting `DATA` back to `"data/"`.
