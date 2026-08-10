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
  the top.
- The plate reads newest first. A food joins at the top row: a slot opens to the row's
  height and the row drops into it from above, out of a cyan wash. Taking one off reverses
  it — the row lifts out and the slot folds shut, and only then does the food actually leave,
  so it can rise back into the search list from below through a slot of its own. The slots
  are wrappers around each row, because the rows carry a `min-height` and `min-height` beats
  `max-height`; `--od-row` tells each slot the height it is opening to, since a phone's rows
  are taller than a desktop's.
- No CORE library. The everyday-food problem is solved in the search order rather than by
  filtering the data, so a long result list costs nothing. SR Legacy is the default; FNDDS
  is the other option. `data/core.json` stays for the root site, which still opens on it.
- Search matches every word of the query, in any order, and treats a plural as its
  singular in both directions — "apple" finds `Apples, raw`, "eggs" finds `Egg, whole, raw`,
  "berry" reaches `Blueberries`. Results are then scored by how the query landed: 20 for a
  whole word, 12 for the start of a longer one, 4 for a hit buried inside one. Filling a
  whole word only reaches the top tier if the query was three characters or more — "t" fills
  the "t" of `t-bone steak` exactly and means nothing by doing so.
  Bonuses mostly settle foods that landed the same way: 10 for being the whole head of the
  name, all of it, before USDA's qualifiers start — `Cheese,` is cheese and `Cheese food,`
  is something else, so it outweighs even being an everyday food, and it can only apply
  where every query word already filled a word of the name. Then 7 for the everyday list,
  up to 3 for landing in the name's first words, and up to 3 for how much of the word the
  query spelled — measured on the singular, so a plural is not a worse match than its own
  singular. Opening the name is worth 1 when the query was a whole word and 9 when it was a
  fragment: a whole word identifies the food by itself, so where it sits hardly matters,
  while a fragment carries nothing else, so typing "j" is a request for foods called
  J-something rather than for `Orange juice`, however everyday orange juice is. A multi-word
  query that opens the name gets the same 9 — "chicken br" is the user typing
  `Chicken breast` from its start, and it outranks the everyday `Chicken, broilers`. The exception is 8 for not being a brand,
  which is a whole tier: nobody searching for a food means a restaurant's version of it
  first, so `T.G.I. FRIDAY'S` loses "t" to `Tomatoes` and `Tofu`. A brand is USDA shouting
  in capitals (`QUAKER`, `MEAD JOHNSON`, `KFC`) or a possessive (`McDonald's`) — which
  catches SR Legacy well and FNDDS barely, since FNDDS keeps its brands inside parentheses
  that generic foods use too (`(Alaska Native)`). Ties go to the shorter name, then the
  alphabet. Nothing about any of it is visible: no badge, no dot.
- The everyday flag is an eleventh element on each food row, written by
  `tools/mark_common.py`; the root site reads ten and ignores it.
- Opening a food on mobile shows the amount two ways, with an `=` between them: grams, and
  the same amount as household servings ("1 MEDIUM", "1 SLICE", "1 TBSP"). Every food has a
  second unit — the quarter of SR Legacy that USDA only ever weighs falls back to OUNCES,
  or to cups and tablespoons if it is a liquid. If OUNCES is the header measure too, that
  pair turns round: your chosen measure on the left, grams on the right, since "28 g = 1
  OUNCES" converts nothing. Whichever side you tap takes the
  − and + — grams move in tens, servings in whole servings, and picking a side does not
  round until a stepper is pressed. The macros follow, a reset arrow (faint until the
  amount moves off the header measure) puts it back, and ADD puts that amount on the plate.
  `tools/add_portions.py` writes the serving onto the food row as a twelfth and thirteenth
  element.
- FULLNESS is checked against evidence rather than asserted. `tools/calibrate_fullness.py`
  matches 33 of the 38 foods in Holt's 1995 satiety index — the only measured satiety data
  there is — to SR Legacy and reports rank correlation, judged leave-one-out: fit on 32
  foods, predict the 33rd. Refitting all six parameters scores 0.795 on the foods it was
  fitted to and 0.530 on one it has not seen, which is overfitting, so the weights chosen by
  judgement stand. One term survived the test on its own and is now in the score: sugar per
  100 kcal at −0.5, which takes the correlation from 0.759 to 0.805. Water was tested too
  and earns nothing — it correlates 0.96 with the bulk term and the fit sets its weight to
  zero every time. The sugar term's known unfairness is that USDA reports total sugars, so
  an apple is charged the same gram as a jellybean.
- An open food is drawn as two rings. The first is all of 100 g — macros, water, ash,
  alcohol when there is any — with the amount in its hole; its macros slice is pinned to six
  o'clock and hands a dashed line down to the second ring, which is those macros on their
  own: protein, carbohydrate, fat, with their total in its hole. Labels stand in a column to
  the right — dot, name, grams — stacked in the order the slices pass the eye, so no callout
  line ever crosses another. The drawing is fixed-pixel: the labels are HTML beside the SVG,
  and the two can only agree on where things are if nothing scales (the template engine
  wraps interpolated text in spans, which SVG will not paint, so the SVG holds geometry
  only). The chosen column's figure keeps the row's top right corner; the reset opens the
  controls row.
- While a search food is open, the plate lends it the height: the summary folds to its
  header line, keeps its total on show, and the copy button gives way to an up chevron that
  closes the food and brings the plate back.
- Plate rows open the same way, with a bin where ADD was, and edit the plate's own amount.
  Collapsed, a plate row just states its grams — the steppers live in the expansion.
- The plate's totals line rides the same three tracks as its rows, so the amount and the
  chosen measure sit under the columns they are totals of rather than in a row of evenly
  spaced figures. Its header carries one control: copy, which puts the plate on the
  clipboard as a tab-separated table — every food with its grams, the same amount as its own
  household measure, and the chosen column — so it pastes into a spreadsheet as columns and
  reads as a list anywhere else. Removal mode is gone with the bin that opened it; a food
  leaves from the bin in its own expansion.

The food libraries are **not** copied into this folder. `index.html` reads them from the
site root via `const DATA = "../data/"`, so the two versions can never drift apart.

Promoting v3 to the root means moving these files up and setting `DATA` back to `"data/"`.
