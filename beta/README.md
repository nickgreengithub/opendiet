# beta

Served at **opendiet.org/beta/**. A copy of the live site, used to try changes without
touching the version at the root. It is `noindex`, carries no social cards, and nothing
links to it.

What is different from the root:

- A launcher screen: the site is a set of small apps rather than one page. FOOD SEARCH is
  the built one; CALORIE CALC, RECIPE BUILDER and FOOD COMPARE are placeholders.
- Desktop switches app with tabs across the top. Mobile gets a back button to the launcher.
- The desktop table wears the donut's own colours: each macro column's bar is its slice's
  hue — protein cyan, carbs green, fat coral, water its blue — sheer enough that the
  figure stays the loudest thing in the cell. WATER rides its own sortable column left of
  PROT, and the macro headers say CARBS and FATS, as the drawing does. The actions header
  carries the same ringed + the mobile rows use: pressing it widens the app and trades
  the CARBS and FATS totals for six sub-macro columns of the same weight as any other —
  SUGAR FIBRE STARCH, SAT MONO POLY — each header wearing its parent's three-letter mark
  (CAR, FAT) pinned at the cell's left in darker type, names six characters at most, no
  unit suffixes, all on the one header line. Every track exists all
  the time (a grid ignores display:none children, which would shuffle every cell that
  follows); collapsed sub tracks are 0rem wide and the two totals make the reverse
  journey, and keeping the track count constant is
  what lets grid-template-columns interpolate, so the whole table — rows, headers, plate,
  totals, even the continuation lines below the last row — breathes as one animation
  rather than snapping. Column gaps are gone (a gap beside a 0rem track is dead space
  that never closes); the cells carry their own padding instead. The sub columns always
  speak grams, whatever basis the macro columns are in. The numeric tracks hold one
  narrow width in both modes — the figures never needed more — so the expansion animates
  only the six sub tracks and the shell, and offscreen rows carry content-visibility so
  a 250-row table isn't relaid out per frame; the two together are the difference
  between a stutter and a glide. Two strong rules and no more: one opens the numeric
  block at WATER, one fences the actions column — everything between is a hairline,
  because two strong lines side by side read as a doubled border.
- Both layouts open on the search line alone, centred both ways — on mobile the magnifier
  and library button step out of the flow so the placeholder holds the exact middle — and
  lift it to the header on the first keystroke. Reaching for the search box, or typing a different query, returns the list to
  the top.
- The plate reads newest first. A food joins at the top row: a slot opens to the row's
  height and the row drops into it from above, out of a cyan wash. Taking one off reverses
  it — the row lifts out and the slot folds shut, and only then does the food actually leave,
  so it can rise back into the search list from below through a slot of its own. The slots
  are wrappers around each row, because the rows carry a `min-height` and `min-height` beats
  `max-height`; `--od-row` tells each slot the height it is opening to, since a phone's rows
  are taller than a desktop's.
- No CORE library. The everyday-food problem is solved in the search order rather than by
  filtering the data, so a long result list costs nothing. SR Legacy is the library; the
  switcher that once offered FNDDS is gone — one good default beat a menu — though the
  FNDDS file still ships for the loader. `data/core.json` stays for the root site, which
  still opens on it. ABOUT, which lived in that menu, is a quiet line on the launcher now.
- Mobile's measure · column selector rides in the search bar itself rather than a bar of
  its own, sharing one type size with the input, and its column names run to eight
  characters at most — FULLNESS, SAT FAT — so the selector never crowds the query.
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
- With OZ as the header measure, the bar under the search says simply OZ behind a small
  monochrome stars-and-stripes flag — the audience that thinks in ounces is one country —
  and the whole drawing speaks ounces with it: the table beside the donut, and the figure
  the hole shows with a macro open, two decimals below ten because most foods are
  fractions of an ounce. Picking any measure also restates an open food's amount as one
  of it, so choosing OZ lands on exactly 1 oz.
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
- An open food is a donut in two equal rings, with two levels of story. At rest it tells
  the whole food: the inner ring is all of 100 g — macros as one light slice, then water,
  ash, alcohol when there is any — and the outer ring rides only the macros slice's arc,
  breaking it into protein, fat, carbs (fat between the two, because cyan and green are
  the pair a tritan eye loses), the run centred at three o'clock to face the table. The
  hole states the split that matters, everything-else / macros of 100: watermelon says
  92/8, parmesan 30/70. With a macro open it says that macro's grams instead, and the two
  figures trade places on the choreography's own clock — the split slips out with the
  flare, the grams arrive as the sweep closes, leave first on the way back, and the split
  returns as the sweep lands, ahead of the final brighten. Each macro's grams is its own layer, so switching
  straight from fat to carbs cross-fades the two figures directly. The sub rows' hairline
  is an inset shadow inside their 30px rather than a border — a border adds height the
  height transition does not govern, and its snap at the end of a switch was a visible
  jolt — and opening and closing share one duration and curve, so when a switch runs both
  at once the two groups' heights cancel exactly and nothing below them moves off-beat. The table sits against the right edge on a subtle interior grid —
  hairlines between rows and before the gram column, no outer border, the gram figures
  held a step off the screen's edge — dot, name, grams,
  with the macro rows indented under MACROS. Fats and carbs are the two slices with more
  to say, so those rows wear a ringed +, pinned against the gram column — unless the
  macro is under 1 g per 100, where there is nothing worth opening and no ring to
  promise it. Only the ring opens: the row's name is a pick like any other row's, so
  tapping CARBS highlights carbs rather than unpacking them. Collapse is more lenient —
  with a macro open, its name, its −, and the drawing itself all fold it. Pressing one
  plays the move rather than cutting to it: the slice first flares bright where it
  stands, then slides in from the outer ring and sweeps the inner one like a clock hand
  until the macro owns the whole circle — the hole handing its split over to that
  macro's grams, in that macro's colour — while its
  own parts fade up on the ring it vacated — saturated, mono, poly for fat; sugars,
  fibre, starch for carbs — and the rest of the donut steps back to quarter strength.
  The outer ring and both sub-rings are dash patterns on pathLength-100 circles rather
  than arc paths, because a dash can wind and an arc cannot. Opening a macro, the rest
  of the donut dulls in the same breath as the flare — the slice is the only bright thing
  from the first frame — then its neighbours wind out dull, the slice slides in (the
  circle's own r) and sweeps the inner ring like a clock hand, and its own parts wind in
  on the ring it left; closing runs the film backwards — the parts wind up first,
  dulled the instant the unwinding starts, the sweep retraces still bright, the resting
  ring winds back in still dull, and brightness returns to everything only after the
  winding has fully landed. The bracket shrinks with the rows it hugs before it fades,
  rather than fading before its shrink can be seen. The row scrolls to the top, and that macro's table
  rows slide open beneath their parent — they are always in the table, holding no height
  and a zero-width border until their macro is pressed, so opening is a height transition
  the rows below ride along with — inside a bracket drawn in the drawing's own pixels,
  possible because every row height and the table's right-hugging width are fixed. The
  open macro's rows lean forward and the rest lean back, the same quarter-step the donut
  takes. Tapping any other row is a pick: its slice brightens above a receding ring, its
  name and figure do the same in the table, and the hole's emphasis swaps with it — a
  water-side pick brightens the left figure, a macro pick the right. Every dim and every lift in the
  drawing is an opaque stroke colour computed in JS — never opacity, which lets the layer
  beneath a slice read as a second, ghost donut, and never a CSS filter, which iOS Safari
  does not apply to SVG elements at all; the rgba shades are composited onto the panel
  first, so no slice is ever see-through. The flare is a stroke tint keyframe for the
  same reason. The brackets are spans rather
  than paths — a span's top and height can animate where a path's d cannot — so each one
  grows, shrinks and shifts with the very rows it hugs. Picking MACROS
  lights the inner macros slice alone and dulls the outer run with everything else, so
  one thing on the ring answers the tap; under a sub pick the sweep dulls harder than
  usual, because a macro's own colour is naturally brighter than its parts and the picked
  part must win. While a macro is
  open, its own sub rows pick in place; any other row folds the macro on its way to the
  pick, quickly — the long unwinding is reserved for a tap on the drawing itself, held by
  a short-lived wind flag so that clearing a pick never waits on the choreography's
  delays. TRANS is wired through the fat breakup — loader, row, slice, remainder — and
  appears the moment the data pipeline runs with FDC nutrient 1257 aboard; MONO and POLY
  say what MUFA and PUFA meant. The ring's position is a constant that nothing beneath it
  may move, and the expansion's height is computed from what the table actually needs. A tap anywhere on the drawing folds it back — the ringed − on the open row says
  so — and the other macro's + presses through and switches directly. Ash stays a top-level part rather
  than a macro, because it is the mineral residue — matter with no energy in it — and the
  macros figure is the food's energy-bearing weight. A whole ring is drawn as two semicircles rather than a 359.8° arc,
  whose butt caps would meet in a hairline seam. The SVG holds geometry only (the template
  engine wraps interpolated text in spans, which SVG will not paint); the hole's figures
  and the table are HTML. The chosen column's figure keeps the row's top right corner; the
  reset opens the controls row.
- While a search food is open, the plate lends it the height: the summary folds to its
  header line, which lays itself on the same three tracks as the rows so the gram and
  chosen-column totals stay on show, right-aligned where they always are, with the ringed
  + on the far left of the title; the copy button steps aside while tucked.
  The fold is also the user's to work: tapping the header of an open summary folds it (and
  closes any open plate row, whose height it was), and tapping a folded one anywhere brings
  it back, closing the open search food that had borrowed the room. The fold animates as a
  grid row going 1fr to 0fr — the one animatable route to a content-sized height, since
  max-height as a length and as a percentage never interpolate, which is why it used to
  snap shut.
- Plate rows open the same way, with a bin where ADD was, and edit the plate's own
  amount. An open plate row sits on its own lighter ground, so the food being edited
  reads as lifted out of the list it came from.
  Collapsed, a plate row just states its grams — the steppers live in the expansion.
- The totals line wears the same ringed + as fats and carbs, on its left so the totals
  keep their right-hand columns, and the whole bar is the button. Pressing it expands the
  bottom bar into the very drawing an open food gets — donut, hole split, table, macro
  rings, picks, the lot — computed for the plate summed as one food: absolute grams
  re-expressed per 100 g, so the same code that explains one food explains the whole
  plate at once. Open, the bar's three shorthands (PRO CAR FAT) step aside for the view's
  name — SUM TOTALS drifts up into their place — and the panel keeps one expansion at a
  time: opening the totals folds any open plate row, and opening a plate or search food
  folds the totals. Nothing else does — a stray tap outside the drawing leaves it be;
  only its own ring, the bar, or a deliberate expansion elsewhere folds it.
- The plate's totals line rides the same three tracks as its rows, so the amount and the
  chosen measure sit under the columns they are totals of rather than in a row of evenly
  spaced figures. Its header carries one control: copy, which puts the plate on the
  clipboard as a shopping list — a dashed line per food with its grams, its own household
  measure in brackets, and the chosen column, then the totals — because the place a plate
  gets pasted is a message, not a spreadsheet. Removal mode is gone with the bin that
  opened it; a food leaves from the bin in its own expansion.

The food libraries are **not** copied into this folder. `index.html` reads them from the
site root via `const DATA = "../data/"`, so the two versions can never drift apart.

Promoting the beta to the root means moving these files up and setting `DATA` back to `"data/"`.
