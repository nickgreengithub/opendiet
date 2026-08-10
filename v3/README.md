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
- An open food is one ring, and a second tier it can grow. The ring is all of 100 g —
  protein, fat and carbs each in their own colour (fat between the two, because cyan and
  green are the pair a tritan eye loses), then water, ash, alcohol when there is any — with
  the macros run centred at three o'clock, facing the table. The hole states the split that
  matters, everything-else / macros of 100: watermelon says 92/8, parmesan 30/70. The table
  sits against the right edge on a subtle interior grid — hairlines between rows and before
  the gram column, no outer border — dot, name, grams, with the macro rows indented under
  MACROS, whose dot is a three-colour pie because that slice of the ring is not one colour
  either. MACROS wears the chevron: tapping it centres a larger ring, grows an outer tier
  riding each macro's own arc — saturated, mono and poly over fat; sugars, fibre and starch
  over carbs — and adds the matching indented rows, the chevron turning up to say the same
  tap folds it back. A whole ring is drawn as two semicircles rather than a 359.8° arc,
  whose butt caps would meet in a hairline seam. The SVG holds geometry only (the template
  engine wraps interpolated text in spans, which SVG will not paint); the hole's figures
  and the table are HTML. The chosen column's figure keeps the row's top right corner; the
  reset opens the controls row.
- While a search food is open, the plate lends it the height: the summary folds to its
  header line, keeps its total on show, and the copy button gives way to an up chevron.
  The fold is also the user's to work: tapping the header of an open summary folds it (and
  closes any open plate row, whose height it was), and tapping a folded one anywhere brings
  it back, closing the open search food that had borrowed the room. The fold animates as a
  grid row going 1fr to 0fr — the one animatable route to a content-sized height, since
  max-height as a length and as a percentage never interpolate, which is why it used to
  snap shut.
- Plate rows open the same way, with a bin where ADD was, and edit the plate's own amount.
  Collapsed, a plate row just states its grams — the steppers live in the expansion.
- The plate's totals line rides the same three tracks as its rows, so the amount and the
  chosen measure sit under the columns they are totals of rather than in a row of evenly
  spaced figures. Its header carries one control: copy, which puts the plate on the
  clipboard as a shopping list — a dashed line per food with its grams, its own household
  measure in brackets, and the chosen column, then the totals — because the place a plate
  gets pasted is a message, not a spreadsheet. Removal mode is gone with the bin that
  opened it; a food leaves from the bin in its own expansion.

The food libraries are **not** copied into this folder. `index.html` reads them from the
site root via `const DATA = "../data/"`, so the two versions can never drift apart.

Promoting v3 to the root means moving these files up and setting `DATA` back to `"data/"`.
