# RECIPE app — paste a recipe, cost it against the food library

A plan, not a build. Written from a full read of `index.html`, the tools and the data, so the
line numbers and names below are real; everything else is the intended design. Build it on a
`beta` branch and merge phase by phase — see "Where it ships".

## Context

OpenDiet is a static single-file app (`index.html` + `support.js`) on GitHub Pages. It has a food
dictionary with pooled "typical" entries (`· avg`) and a plate (MY FOOD SUMMARY) that sums chosen
foods at chosen grams. The new direction: paste a recipe, have each ingredient line matched to
the nearest library food, and see the recipe's calories and macros — in the same UI as the plate,
titled MY RECIPE, with a SUBMIT / SUBMIT & REVIEW choice and a REVISE affordance per row.

Decided:
- Unit→grams uses a **generic unit table now**, structured so FDC's full per-food portion table
  can drop in later with no UI change (the FDC CSVs were not to hand when this was written).
- The recipe is a **separate list** from the plate; totals shown whole and **per serving**.
- Mobile-first, reusing the existing designs (donut, steppers, summary panel).

**Open: where the AI runs.** The matcher needs two things a string match cannot know — that
"caster sugar" is sugar and "double cream" is heavy cream, and that a recipe's "onion" is
`Onions, raw` rather than the frozen one. Two ways to get that knowledge in:

| | Build-time (no worker) | Runtime (Cloudflare worker) |
|---|---|---|
| How | An alias table generated once by an LLM, tested against the real ranker, committed as JSON | Each paste goes to a worker that calls Claude Haiku with the lines + candidate names and returns structured matches |
| Coverage | The few hundred to couple thousand ingredients people actually cook with; misses the long tail unless added | Anything |
| Rough hit rate | ~85–90% of lines on typical recipes | ~95%+ |
| Cost / infra | None; the site stays a static file | Cloudflare account, `wrangler login`, a secret, a rate limit; fractions of a cent per recipe; the recipe text leaves the browser |

The plan below is written **local-first**: the worker is not required, and the parsed-line shape
(Phase 1) is the contract a worker would return, so adding one later is purely additive — a
Phase 9 that swaps `matchLine` for a fetch with the local matcher as fallback. The worker's setup
is interactive (`wrangler login`, secrets) and belongs in a terminal session. Either way the
REVISE UI (Phase 5) is what makes the misses tolerable, so it is not optional.

Measured facts that shape the plan:
- A naive word match over 35 typical ingredients (with stemming) misses 9 outright on vocabulary
  ("caster sugar", "double cream", "bell pepper", "tinned tomatoes"…) and picks the wrong sibling
  where world knowledge is needed ("onion"→frozen, "chicken breast"→deli slices, "milk"→shakes).
  Recipes mean **raw** ingredients; the matcher must prefer raw/plain entries.
- 1,476 foods carry a CUP measure and ~480 a TBSP/TSP one, so volume→grams can use the food's own
  density (`pg`/`pn`) first; a generic density table is only the fallback.
- **The prune removed baking staples**: `Sugars, granulated/brown/powdered`, `Leavening agents,
  baking powder`, `Vanilla extract`, `Syrups, maple`, `Cornstarch`, two vinegars — all foods whose
  fibre-zero or sugar-zero is real. `Salt, table` was never in the library. Water and black
  pepper are. Sugar is in every baking recipe, so this must be fixed as part of the feature.

## Where it ships

- Work on `beta`, reset onto `main` first (`git checkout -B beta origin/main`), one commit per step.
- Each shippable phase is merged to `main` **hidden behind `FULL_SITE`** (index.html:1206): add
  `recipe` to `APPS` (2940) and `live()` (2968) and opendiet.org never shows it, while
  `opendiet.org/?full=1`, localhost and `*.github.io` do. This is the repo's own convention for
  unfinished apps (game, calc). Pages only deploys `main`, so this is the only way the user can
  open it on a phone without a second site.

## Phases (each verifiable on its own; effort in relative units)

| # | Phase | Deliverable | Effort |
|---|---|---|---|
| 0 | Data fix | Put the pruned staples back with a principled exemption | S |
| 1 | Parser | `parseRecipe(text)` in `recipe.js` + node tests | S |
| 2 | Matcher + alias data | `rankFoods` extraction; `data/aliases.json`; `tools/recipe_aliases.py`; `matchLine`; labelled hit-rate test | L (highest risk — do first after parser) |
| 3 | Unit conversion | `data/units.json`; `gramsFor(line, fo, units)` + tests | M |
| 4 | Mobile UI | launcher card, tab, compose screen, MY RECIPE panel, servings | L |
| 5 | Review / revise | scoped candidate search, SUBMIT & REVIEW stepping, ghost rows | M |
| 6 | Desktop | table reuse, textarea placement, revise column | M |
| 7 | Persistence + copy | `od-recipe` localStorage, library-switch rematch, copy text | S |
| 8 | Docs + harness | README / DESIGN / data README; screenshot harness | S |
| 9 | Worker (optional, terminal) | Cloudflare worker calling Claude Haiku; `matchLine` falls back to local when it is absent or fails | M |

Phases 1–3 are pure functions with no UI and are reviewed on test output alone.

## Phase 0 — restore the pruned staples (`tools/prune_unmeasured.py`)

The category rule ("SWEETS almost always carry fibre, so a fibre-zero is a gap") is right in
general and wrong for a food that has no room for fibre. Add two exemptions, each argued in the
docstring like the rest of the file:
- **Fibre zero is measured when sugar already accounts for the carbohydrate**: `sg >= c - 1.0`.
  Covers sugars, syrups, vanilla extract, honey.
- **A keep-list for the handful the numbers cannot rule on** (`Cornstarch`, `Leavening agents,
  baking powder`, vinegars): names somebody has looked at, written in the tool with a line each.
Rebuild from the pre-prune file (`git show a337346^:data/legacy.json` → prune → `pool_foods.py`)
— no FDC CSVs needed. Run `tools/audit_data.py`. Same for `survey.json` (check which staples it
lost). Update `data/README.md` Missing-figures section. Salt is the one staple that is genuinely
absent: the parser treats it (and "salt and pepper to taste") as a **zero-energy line**, shown as a
row with 0 kcal, never a failed match. No `pantry.json` — one library, one truth.

## Phase 1 — parser (`recipe.js`, `parseRecipe(text) → rows[]`)

One flat object per input line — **this is the contract a future Worker step would also return**
(it fills through `conf`; everything after is app-owned):

```
{ i: 3, raw: "2 tbsp olive oil, extra virgin",
  kind: "ing",                       // "ing" | "head" | "note" | "blank" | "zero" (salt/pepper/water)
  qty: 2, qtyText: "2", qtyLo, qtyHi, // ranges "1-2" → qty 1.5
  unit: "tbsp", unitText: "tbsp",    // canonical key from units.json, or null
  ing: "olive oil", prep: ["extra virgin"],
  state: null,                       // "raw"|"cooked"|"canned"|"frozen"|"dried"|null — what the LINE says
  flags: { opt: false, taste: false },
  food: "Oil, olive, salad or cooking", cands: [...top 8 names...], conf: 0.82,
  // app-owned:
  grams: 27, gramsHow: "pg"|"mass"|"density"|"count"|"default"|"none", label: "2 tbsp",
  review: false, user: false, off: false }
```
Rows are keyed by `i` (two lines may match the same food); grams live on the row, not in `s.qty`.

Per line: normalise (NFKC, unicode/ascii fractions, "1 1/2", bullets, numbering) → classify
(`head` for "For the sauce:", ALL CAPS, "Serves 4" — which sets servings; `note` for method steps:
imperative verb without a leading quantity, or >12 words) → quantity (numbers, ranges, number
words, "a handful/pinch/dash/knob/splash" set qty 1 + that unit; "juice of 1 lemon") → unit
(table-driven spellings; "2x400g tins" → 800 g; parenthetical mass overrides; small/medium/large
is a unit only before a noun) → ingredient/prep split at first `,` `(` ` - ` `;` plus a PREP word
set (chopped, diced, minced…) and a STATE word set → flags (`optional`, `to taste`).

## Phase 2 — matcher (`matchLine(line, foods, aliases) → {food, cands, conf, review}`)

**Extraction first, own commit.** Move `stemWord` (index.html:1115), the `mkFood` closure
(2272–2331) and the inline scorer (2819–2891, constants WHOLE_PTS…POOL_PTS) into `recipe.js` as
`OD.stemWord`, `OD.mkFoods(json)`, `OD.rankFoods(list, q)`; `renderVals` calls
`src = OD.rankFoods(src, q)` at 2848, sort at 2914 unchanged. `recipe.js` is a classic
`<script src="./recipe.js">` after `support.js` (line 37), exposing `window.OD` with a
`module.exports` guard so `node` can run the identical code. Guard the extraction with the
existing smoke harness: same top-6 for "egg, whole", "kale", "beef" before and after.

**`data/aliases.json`** (~300 hand-seeded entries, longest phrase wins, stemmed both sides):
```
{ "m": ["caster sugar","granulated sugar","white sugar","sugar"], "pin": "Sugars, granulated" }
{ "m": ["bell pepper","capsicum"], "q": "peppers sweet raw", "keep": ["red","green","yellow"] }
{ "m": ["tinned tomatoes","canned tomatoes","chopped tomatoes"], "q": "tomatoes canned", "state": "canned" }
{ "m": ["onion"], "q": "onions raw", "keep": ["red","spring"] }
```
`m` phrases; `q` the query for `rankFoods`; `pin` an exact name placed first if present in the
current library; `keep` line words appended to `q` (colour, cut), falling back to bare `q`;
`state` the state the alias implies; optional `cat`.

**Scoring**: alias lookup on `ing` (else `ing` minus stopwords: fresh, of, good, quality,
organic…) → `rankFoods` → recipe re-weighting as a second pass in `matchLine` (never inside
`rankFoods`): `+8` raw/plain, `-10` per process word in the name (frozen, dehydrated, dried,
canned, cooked, boiled, baked, fried, roasted, juice, babyfood, restaurant, fast foods, shake,
mix, powder, with salt…) unless the line's or alias's `state` names it (`+6`), `+40` pin,
`-0.2 × name length`. Retry with the head noun only if empty (mark `weak`).
`conf = clamp((h1−h2)/h1) × (aliasHit ? 1 : 0.7)`;
`review = !food || (!aliasHit && conf < .25) || weak || gramsHow === "none" || brand`.

**Offline tooling `tools/recipe_aliases.py`**: `--check` runs every alias phrase through the
real ranker (shell out to `node -e` requiring `recipe.js`, so the two never drift) and warns
where #1 ≠ `pin`; `--suggest phrases.txt` prints the 15 nearest library names per phrase so the
author can ask an LLM offline and paste reviewed rows back. No API call in the repo.

**Labelled test set in the repo**: `tools/recipes/*.txt` (3 real recipes: a curry, a bake, a
salad) + `tools/recipe_expect.json` (`{"raw","food","g":[lo,hi]}` per line). Pass bar: ≥85%
top-1, ≥95% top-8. Expect a second alias pass after the first run.

## Phase 3 — units (`data/units.json`, `gramsFor(line, fo, units) → {g, how, label}`)

```
{ "mass": {g,kg,oz,lb}, "volume": {ml,l,tsp,tbsp,cup,floz,pint,pinch,dash,splash},
  "density": { "word": [["icing sugar",.56],["sugar",.85],["honey",1.42],["flour",.53],["oil",.92],…],
               "cat": {"FATS":.92,"DAIRY":1.03,"GRAINS":.6,…} },
  "count": { "default": {clove:3, slice:25, can:400, bunch:100, handful:30, sprig:2, medium:110, large:150,…},
             "word": { "onion":{small:70,medium:110,large:150,each:110}, "garlic":{clove:3,head:40}, "egg":{…}, … } },
  "labels": { "MEDIUM":["medium","each"], "SLICE":["slice","rasher"], "CUP":["cup"], "TBSP":["tbsp"], "TABLESPOON":["tbsp"], "CLOVE":["clove"], "CAN":["can","tin"], … } }
```
Resolution order (first hit wins, `how` records it): (1) `fo.pt` — the future per-food portion
table, element 21, absent today, wired now so `tools/add_portions.py --all` is a pure data
upgrade; (2) mass unit; (3) volume: if `labels[fo.pn]` contains the unit → `qty × fo.pg ×
volume[unit]/volume[label]` (FDC's own density), else `qty × ml × density` (word, then
category, then 1.0); (4) count: `labels[fo.pn]` → `fo.pg`, else `count.word[head]`, else
`count.default`; (5) qty with no unit ("2 onions") → `each`; (6) neither → `taste ? 0 : 100`,
`how:"none"`, `review:true`. Cap `RCP_MAX = 5000` g (not the plate's 990).

## Phase 4 — mobile UI

**Launcher / tabs**: `APPS` gains `{ k:"recipe", label:"RECIPE", icon: ICON_RECIPE, note, card }`;
`appCards` (4808) and `appTabs` (4792) pick it up. Four tabs on a 360 px phone: tighten
`tabBar` gap and hide `tabAbout` on narrow (ABOUT is on the launcher). Verify at 360×780.
`setApp("recipe")` lazily fetches `aliases.json` + `units.json` into `this._rcpData`
(pattern: `loadDeck()` 1561).

**Skeleton**: new `sc-if isRecipe` block after the `isResults` block closes (~1075), mirroring the
search app's mobile column (849): top area, bottom panel, `popScrim` reused.

**Compose** (`s.rMode === "compose"`, default when no rows): bar `mRcpBar` (clone of `mSearchRow`
at 2.9 rem) with "PASTE A RECIPE" left and a `− 4 SERVES +` stepper right (built from
`stepL/stepR` + `amtNumBase`); a `<textarea data-search="c" data-compose>` filling the top area
(`flex:1; min-height:0; resize:none; overflow:auto`) — it scrolls itself, never the document, so
`_unscroll` (1377) is not fought, and `data-search` lets `_focusIn/_focusOut` (1379–1402) set
`s.kb` so the shell sizes to the visual viewport as it does for search; an action row
`mRcpActs` (3.3 rem, like `mMeasureRow`): muted CLEAR left, `SUBMIT & REVIEW` bordered and
`SUBMIT` filled (`mAddBtn` style) right. Submit: `blur()` the textarea (as `toggleSum` 2445 does),
`runRecipe(review)` → parse → match → grams → `setState({recipe, rMode, rStep})`, panel rises
with `data-rise`.

**Result** (`rMode === "result"`): top area shows the recipe collapsed to a card `mRcpPeek`
(first `head` line or "RECIPE" · "12 INGREDIENTS · 3 TO CHECK" · chevron; tap → compose with
text intact). Panel `mRcpPanel` = `mSumPanel` (6726) with `data-plate data-rise`, `maxHeight`
85%; header = `mSumHead` grid, title **MY RECIPE**, tucked peek (`sumTuckQty/Val`), `copyBtn`,
plus a REVIEW ring badge with the review count (in `--fat` when > 0) that starts stepping.

Rows via a new `mkRecipeRow(row)` beside `sumRows` (3993), reusing `mSumRowBase`, `SUM_COLS`,
`sExpand`, swipe-to-remove (4120–4170, keyed by `row.i`), `sToggle` → `s.rOpen`,
`ctl = amountCtl(fo, row.grams, g => setRowGrams(i, g), s.rGMode, …)` (3018, unchanged
signature), `vizFor(fo, row.grams, …)` for the donut:
- **Name cell is two lines**: line 1 the ingredient as written ("olive oil", body colour);
  line 2 the matched USDA name (`.78rem`, `--muted`, ellipsis) with an `AVG n` badge when it is a
  pool. The user reads their own recipe and spots a wrong match by comparing the lines; the USDA
  name alone truncates to nothing in the track; and line 2 is precisely what REVISE changes, so it
  must be visible on the closed row. Row `minHeight` 3.1 rem.
- Qty cell: line 1 `grams g` (or ml), line 2 the original "2 tbsp" (`.7rem`, chrome face) so the
  conversion is auditable. Value cell: the chosen `mCol` value, as on the plate.
- The reserved `borderLeft` on `mSumRowBase` becomes the status mark: `--fat` unmatched, cyan
  `.6` needs review, transparent confirmed. `opt` rows at `.7` opacity; `taste`/`zero` rows show
  "to taste" / "0 g".
- **Ghost rows** (`food:null`): line 2 "NO MATCH · TAP TO FIND" in `--fat`, qty/value "—",
  excluded from totals; tap opens revise for that row; swipe/DEL sets `off:true` (folds with
  `data-gone`).
- Expanded row: donut + `vTable`, then `mMeasureRow` (reset / grams stepper / `=` / serving
  stepper when `fo.pg`), then `REVISE` (bordered, swap icon) and `DEL` (`mBinBtn`).

Totals: a `rServRow` (2.2 rem) above the totals row — left a two-face `WHOLE | PER SERVING`
switch in the `dMeas100S/dMeasOzS` style (4593), right the `− 4 SERVES +` stepper; then
`mSumTotRow` reused with `mTotLabel` "RECIPE TOTAL" / "PER SERVING", figures divided by servings
when per-serving (rows rounded first then summed, like `tKDisp`). **Rows always show whole-recipe
amounts** — editing a row edits the recipe; per serving is a division of the result shown once.
Totals donut via the `foTot` pattern (4292) with `s.rTotOpen`.

**Mutual exclusion**: `rOpen`/`rTotOpen` join the open-surface set — `setApp` (2973),
`toggleRow` (3687), `sToggle` (4055), `exitScope` (6708) clear them; the recipe's toggles clear
`mOpen`, `sOpen`, `totOpen`.

## Phase 5 — review / revise

`openRevise(i)` (one row) or `rMode:"review"` stepping through `review` rows only
(`SUBMIT & REVIEW` = `runRecipe(true)` then step from the first). The top area swaps to the
**scoped search** — the pool drill-in pattern (6706–6720, template 854): `mSearchRow` with the
scope chip showing the ingredient in caps (and `2 / 5` when stepping), back chevron = keep and
advance (SKIP), input empty with placeholder "SEARCH FOR A BETTER MATCH". The list is the row's
`cands` through `mkRow` (2645) under a "CANDIDATES" caption; once the user types, `rankFoods`
over the whole library replaces them. A tap **assigns** (`assignMatch(i, name)` → `food`,
`user:true`, `review:false`, grams recomputed via `gramsFor`) instead of opening. While a scope is
open the panel is folded to its header as it is when `mOpen` is set, showing the running total.
After assign: stepping → next review row; single revise → back to result. When the last is done,
`rMode:"result"` and the badge count is 0.

## Phase 6 — desktop

Inside `isRecipe`, a desktop block mirroring 713–848: `dFrameCol` + the same column heads. The
`dSearchCell` (724) becomes, in result mode, "MY RECIPE · SERVES [input] [−][+] · WHOLE | PER
SERVING"; in revise mode the existing scope chip + input (727–729). `dBody` (746): compose = the
textarea filling the rows area (`padding-right:10px` keeps the scrollbar reserve) with
`SUBMIT & REVIEW / SUBMIT / CLEAR` right-aligned beneath; revise = candidate rows (748–776
unchanged, tap assigns). `dRcpWrap` = `dSumWrap` (4498) titled MY RECIPE; rows = the desktop
plate cells (785–803) with the name cell "olive oil — Oil, olive, salad or cooking" (USDA part
in `--muted`), the typed qty `<input>` (`onQty` pattern 4209, cap 5000) followed by the "2 tbsp"
hint, and two action buttons: swap (REVISE, `dAddBtn` style) and minus (`dDropBtn`). Totals row
(828–844) label toggles WHOLE/PER SERVING; copy button reused. Mark `dRcpWrap` `data-plate`.

## Phase 7 — persistence and copy

localStorage key **`od-recipe`**: `{ v:1, lib, text, servings, per, rows }` (never touches
`nutri-search-sum`); `saveRecipe()` on every change (pattern 2459), hydrated beside 1290; on
load with rows → `rMode:"result"`. Library switch: rows whose `food` is absent in the new
library are re-matched (`user` rows keep `food` if it exists, else `user:false, review:true`);
grams recomputed only where `gramsHow === "pg"`. Copy: `recipeText` beside `plateText` (4344),
same dash-led voice, whole then per serving, unmatched lines listed as "(no match)".

## Code change checklist

- **New**: `recipe.js` (stemWord, mkFoods, rankFoods, parseRecipe, matchLine, gramsFor,
  recipeTotals; `window.OD` + `module.exports`); `data/aliases.json`; `data/units.json`;
  `tools/recipe_aliases.py`; `tools/recipes/*.txt`; `tools/recipe_expect.json`.
- **`tools/prune_unmeasured.py`**: the two exemptions; rebuild `data/legacy.json` and
  `data/survey.json` from their pre-prune files; re-run `pool_foods.py`, `audit_data.py`.
- **index.html**: constants `ICON_RECIPE`, `RCP_MAX`, `RCP_CANDS` near 1246; delete `stemWord`
  and the `mkFood` closure in favour of `OD.*`; replace the scorer with `OD.rankFoods`; state keys
  `recipe, rMode, rOpen, rGMode, rTotOpen, rStep, rScope, rText`; methods `loadRecipeData,
  runRecipe, assignMatch, setRowGrams, dropRow, openRevise, nextReview, setServings, saveRecipe,
  copyRecipe` (uses `copyPlate(text)` 2479); `APPS`/`live`/`setApp`; `renderVals` bindings
  (`isRecipe, rRows, rTot, rTotViz, rServ*, rTextarea, mRcpBar, mRcpActs, mRcpPeek,
  rReviewCount`); the `isRecipe` template blocks; `data-plate` on both panels.
- **Docs**: README "What it does" + layout table (`recipe.js`, the three data files); DESIGN.md
  section "The recipe app" (why local matching, why two-line rows, why per serving is a division,
  why a second script); `data/README.md` sections for aliases/units and the prune exemptions.

## Verification

- **Node**: `node tools/recipe_test.js` requires `recipe.js`, builds foods via `OD.mkFoods` from
  `data/legacy.json`, loads aliases/units, runs the three recipes, asserts `kind` counts, per-line
  match and grams range from `recipe_expect.json`, prints hit rate; fails under 85%/95%. Fixed
  parser cases for every quantity/unit form.
- **Browser** (existing harness: playwright-core at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`,
  vendored React in the scratchpad `vendor/`, `setsid python3 -m http.server 8765 --bind 0.0.0.0`,
  page `http://127.0.0.2:8765/index.html?full=1`): 390×844 @2× mobile — tap RECIPE, fill
  `[data-compose]`, SUBMIT, assert `[data-plate] [data-row]` count and totals text; screenshot
  compose / result / expanded row / review scope; walk SUBMIT & REVIEW to the end; light and dark.
  Repeat at 1440×900. `pageerror` must be empty.
- **Regression**: re-run the existing search smoke scripts after the `rankFoods` extraction (same
  top results for "egg, whole", "kale", "beef"); `tools/audit_data.py` passes after the rebuild;
  the plate is untouched (add/remove/qty still work).

## Risks / open points

1. Match quality is the whole feature; alias coverage is hand-seeded and will need a second pass
   after the first labelled run.
2. The `rankFoods`/`mkFood` extraction touches the search path — its own commit, smoke-guarded.
3. iOS textarea inside the `position:fixed` shell is a new case for `_vv`; test on a device before
   merging Phase 4.
4. Four tabs on a 360 px phone — verify; hide ABOUT on narrow rather than shorten labels.
5. Steppers in tens are coarse for "1 kg flour"; desktop has a typed input; revisit later.
6. A pool as the match is preferred by score, which suits recipes; confirm the AVG badge reads on
   a second line.
