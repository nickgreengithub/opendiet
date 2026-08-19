# OpenDiet

**[opendiet.org](https://opendiet.org/)** — protein, carbs, fat and calories for 16,000+ foods, in one searchable list.

No account, no tracking, no food diary. Type a food, read the numbers, compare it against
anything else. That is the whole product.

## Why

The data is public. USDA FoodData Central publishes it, it is public domain, and anyone can
download it. But actually *reading* it is another matter — the official site is built for
querying one food at a time, most nutrition sites bury the numbers under adverts and
sign-up walls, and the reference site people used to point to — NutritionData — was bought
and is long gone.

So there was no fast way to answer a question as ordinary as "how much protein is in lentils
versus chickpeas, per calorie?" without opening several tabs and doing arithmetic.

This is that missing page. One table, every number visible at once, sortable by any column.

## What it does

- **Search and sort** any column — water, protein, carbs, fat, calories, or name.
- **Expand the table** and each macro breaks into its parts: sugar, fibre and starch under
  carbohydrate; saturated, monounsaturated and polyunsaturated under fat. Every column
  explains itself on hover.
- **Two measures.** Read everything per 100 g/ml or per ounce; the whole table follows,
  figures and portions alike.
- **Open a food** and it is drawn rather than listed — a donut of what the food actually is
  (most food is mostly water), with its macros on a ring of their own, and a table beside it.
  Press a macro and it slides in and breaks into its parts.
- **Build a plate.** Added foods drop into a summary with running totals, their portions
  typed in directly, and a copy button that puts the plate on the clipboard as a shopping
  list. Saved in your browser, not on a server.
- **A fullness score** per food — a per-calorie index built from macro energy shares, fibre
  density and the sheer bulk a calorie buys. The plate carries the weighted average of its own.
- **Thermic effect toggle.** Deducts the energy digestion itself costs: 25% of protein calories,
  8% of carbohydrate, 2% of fat.

There is deliberately no daily target to measure a plate against: turning a calorie figure
into a protein or carbohydrate goal is contested enough that the table would be taking a
side it has no business taking. It states what is on the plate.

On a phone the site opens on a launcher: three rows of one height, each with a mark, a
name and one short line. All three open. A desktop opens straight into the table, with the
others a tab away.

A tablet runs the phone's design, because below 1000px of width the table can no longer
name a food — but it runs it at a tablet's size rather than a phone's. Everything steps
up one notch together: type, rows, controls, the drawings, and the column they sit in.
The column is held off the glass by real gutters instead of running to the bezel, and
there is no frame around it, because a bordered column on a big screen reads as a phone
app someone parked there.

## Calorie game

A second app. On a phone the pair is stacked; on a desktop it is side by side, the two
photographs taking the whole screen between them. It opens by showing the game rather than describing it — HOW TO PLAY, one line of
instruction, and a working miniature of a round that plays itself on a loop, a hand pressing one of two cards
and the figures arriving, the hand a cursor sweeping between them on a desktop — and then asks one question six times: two foods stacked one
above the other, each with the portion it is, and which of them carries more calories.

The portion is drawn as well as written. USDA measures these 36 foods in 14 different
units — cups, tablespoons, slices, fruit, halves, containers, rashers — which collapse to
four shapes on the card: a cup, a spoon, a slice, a whole item, repeated as many times as
the portion says and set to the right of the label. Three cups of courgette is three cups.
A tall glass of milk is one and a half, so the half is drawn faint. The marks themselves
are Material Design Icons, inlined as paths.

Tap a card and both photographs fall away into the dark while a donut rises over each, with
the calories in the hole. The donut is drawn against the largest figure in that whole game
rather than against its own partner, so a three-quarter ring means the same thing in every
round and the sixth reveal can be compared with the first. The pair then slides out to the
left as the next arrives from the right. There is no button to press and nothing scrolls.

The first answer of a session — and only the first — holds the round and puts up a card
saying whether it was right and which food actually carried more, since a donut and two
figures mean nothing to someone who has never played. It goes on a tap and does not come
back until a fresh session.

Which round it is sits at the bottom left, and six boxes at the bottom right fill with a
tick or a cross as the game goes, so how you are doing and how much is left read in one
glance.

The end is a grade and six tiles. The grade is a letter on percentage correct, with the
percentage and the tally beside it, on the school scale stretched to fit a game where
guessing scores about half: half is a D, the floor of a pass, and anything below it — worse
than a coin toss — is an F. Under it the six pairs in the order they were played, drawn as the food table draws
itself — sentence-case names, portions beside them, calories right-aligned under a KCAL
head, one hairline under every row — with each pair a block of two lines closed by a
hairline and real air between the blocks. The tick or cross sits against the line that was
actually pressed rather than at the top of the pair, and the lighter plate's figure goes
down a step, so which food was chosen and which way the pair went both read without
comparing two numbers. The caveat sits behind a mark rather than
on the page.

That is the phone. A desktop ends on the food table instead: the same grade and score,
then the site's own thirteen columns — water, protein, sugar, fibre, starch, carbs,
saturated, mono, poly, fats, calories — one row per food and two rows per pair, in the
order they were played. The calorie column is lit, because it is the column the game was
about, and the tick or cross sits against the chosen food's calories in that food's row.
Nothing opens, since every figure is already on the page.

On a phone, tap a pair and it unfolds into a comparison: the two foods in two columns, every macro and
sub-macro the site lists, calories at the foot, both at the portion the round showed. The table stands in
place of the two rows rather than under them, and the two names travel from their rows into
the column heads as it opens — and back again when a tap anywhere else puts them away. In each
row only the larger figure is lit, so a column of white shows where a food is heavy before a
number is read; the foot is grams, then calories under it with the round's tick or cross. There is no amount control and no ADD button — the portion is the question,
and there is no plate in the game. Set against the grade itself are two lines: the score, and the
plate that surprised you most — the widest gap you got wrong, named, since picking the
lighter plate means the heavier one was worth more than you gave it credit for. It closes
on a caveat: calories drive body fat, but a healthy diet also means hitting macro and
micronutrient targets, and this is a game rather than nutritional advice. That sits at the
end rather than the start, because that is the moment someone might take a score about
calories for a verdict about food.

**The deck is built so that size cannot answer the question**, and that is measured rather
than hoped for: across its 399 playable pairings the bigger portion carries more calories
51% of the time, so always picking the fuller plate scores a coin toss. Getting there is
not a matter of matching sizes or matching calories — either of those just hands the
player the opposite shortcut. It is a matter of having, at every size, both a cheap food
and an expensive one. One carrot is 25 kcal and half a cup of almonds is 428, and both sit
on a small plate. Three cups of cucumber is 47 and two cups of brown rice is 497, and both
fill a large one.

36 foods in portions a person would actually serve — three tablespoons of olive oil is a
dressed salad, not a thimble — and the weight is never typed in: it is USDA's own published
household portion for that food multiplied by a whole number, with the calories taken from
that weight against USDA's own energy density.

The pictures are generated rather than photographed, and every one is counted against its
label before it is used. Three of the 36 came back holding something other than what was
asked — seven strawberries not eight, four rashers not three, a whole bar of chocolate
rather than half of one — and were relabelled to what they actually show.

## Calorie calc

A third app: what a body spends in a day, and what happens if you hold a number.

Seven questions, one per screen — sex, age, height, weight, body fat, how the day is spent,
how you train — and then a screen with two sliders on it. The inversion is the whole idea:
**the input is calories and the output is a body**, rather than naming a goal and being
handed a number. Nobody types a target weight. Move the intake slider and the figure, the
body fat percentage and the date all answer; move the time slider and the year plays.

Body fat is not asked for as a number. It is estimated from height, weight and age, shown
as an estimate, and picked off a row of reference figures — and the moment it is stated
rather than guessed, the resting-metabolism equation switches to the one that reads lean
mass instead of weight. Activity is two questions rather than one, because the day you
spend anyway and the training you choose are estimated differently and priced differently:
the first on the FAO lifestyle bands read at their exercise-free end, the second in METs,
at `(MET − 1) × kg × hours` — the −1 because resting metabolism is already counted once and
an hour of training is not an hour of extra existing.

The trajectory is not 3,500 kcal a pound. That rule is static, and applied to a year it
overestimates badly. The deficit here is applied against a maintenance recomputed every day
from the body that is actually left, with the fat and lean split by Forbes — the leaner you
are, the more of each kilogram is muscle — and with adaptive thermogenesis ramped in over
eight weeks. Checked against Hall's published rule of thumb, a 100 kcal/day deficit gives
2.7 kg at a year and 4.3 kg at three, against his 2.2 and 4.5.

Behind a mark are the curves: weight, fat mass and lean mass on one axis, and under them
the line nobody draws — maintenance falling to meet the intake, which is why the twelfth
month does less than the first.

The figure is a body, and it turns. It is a glTF carrying one mesh and seven morph
targets — five fat levels blended continuously, plus a muscle pair driven by lean mass —
so at a constant weight, sliding body fat down makes a fitter body rather than a smaller
one, which is what the arithmetic says it should do. Moving a slider moves the body
rather than cutting between pictures, and on the result screen it is driven by the
scrubbed trajectory: dragging through the year *is* the animation. Three.js is vendored into the
repo and loaded only when this app is opened, and a browser without WebGL gets a line
drawing instead.

The mesh is baked by `tools/makehuman_bake.py` from the
[MakeHuman](http://www.makehumancommunity.org/) community's base mesh and morph-target
library, released CC0 — each fat level is their sculpted body with their own weight and
fat targets composed numerically, the arms lowered by their skeleton's skin weights, no
Blender in the loop. [`CALC.md`](CALC.md) is the plan, with every equation cited.

## The data

From USDA FoodData Central, committed to this repo as static JSON:

| Library | Foods | Source release |
|---|---|---|
| SR LEGACY | 7,756 | SR Legacy, 2019-04-02 |
| SURVEY FNDDS | 8,661 | Survey (FNDDS), 2020-03-31 |

SR Legacy is what the site reads. The everyday-food problem is solved in the search
ranking rather than by filtering the data, so no curated subset is needed and a long
result list costs nothing.

Values are per 100 g, or per 100 ml for foods measured by volume — FoodData Central's own basis.
A blank cell means USDA reports no value for that nutrient, not that the value is zero.

USDA FoodData Central is a work of the US federal government and is in the public domain.
See [`data/README.md`](data/README.md) for the exact nutrient ids, the category mapping, and how
to regenerate the files.

Numbers are averages for a generic item. Brand, cut, ripeness and cooking method all move them.

## Running it

There is no build step, no dependency install and no package manager. The repo root *is* the
site. Serve it with anything:

```sh
python3 -m http.server 8000
# then open http://localhost:8000
```

Opening `index.html` from the filesystem will not work — the food libraries are fetched over
HTTP, and `file://` blocks that.

The one runtime dependency is React, which `support.js` loads from unpkg at boot. Everything
else — the data, the design system, the fonts — is served from this repo.

## Layout

```
index.html          the whole app: markup, styles and logic
support.js          the small framework index.html is written against
ds/                 design system — tokens, stylesheet, fonts
data/               the three food libraries as JSON, plus their provenance
tools/              one-off generators (data build, preview image, body meshes); not part of the site
body.js             the calc app's figure — glTF morph targets in Three.js
vendor/three/       Three.js and GLTFLoader, vendored rather than fetched from a CDN
DESIGN.md           why it is built this way — the long version of this README
CALC.md             the plan for the third app, with its sources
```

One copy of the site, at the root, deployed by GitHub Pages from `main`. There is no
staging copy and no promotion step — `beta/index.html` is a redirect to the root and
nothing else, so an old bookmark cannot land on a stale build.

## Licence

[PolyForm Noncommercial 1.0.0](PolyForm%20NonCommercial%201.0.0.txt).

Free to use, copy, modify and share for any **noncommercial** purpose — personal use, research,
teaching, charitable work. Commercial use needs a separate licence; open an issue if you want one.

This is source-available rather than open source in the OSI sense, since that definition does not
permit a restriction on commercial use.

The USDA data itself carries no such restriction — it is public domain and you can do anything
you like with it.

The four portion marks in the calorie game are from
[Material Design Icons](https://pictogrammers.com/library/mdi/), used under the Apache
License 2.0 and inlined as SVG paths.

The calc app's body meshes are derived from the
[MakeHuman](http://www.makehumancommunity.org/) project's base mesh and morph targets,
released by the MakeHuman Team as **CC0** — thank you. The bake is
`tools/makehuman_bake.py`; the upstream data is not committed here, the script says
where to fetch it.
