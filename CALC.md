# Calorie calc — plan

**Status: built and live, with the body render still a placeholder.** The seven-step run,
the model, both sliders and the curves panel are working; where the rotating figure will go
there is a line-drawn person holding the space. Sections 5 and 8 are the outstanding work.

The third app. FOOD SEARCH answers "what is in this?"; CALORIE GAME answers "which is
bigger?"; CALC answers "how much, and what happens if I hold it?"

Mobile first, because the launcher is the phone's front door and CALC is the only tile on
it that has never opened. A desktop layout follows from the same model.

---

## 0. The stance problem, first

The README currently says, of the food table:

> There is deliberately no daily target to measure a plate against: turning a calorie
> figure into a protein or carbohydrate goal is contested enough that the table would be
> taking a side it has no business taking. It states what is on the plate.

CALC is a target calculator. That is not a contradiction, but it is only not a
contradiction if the line is drawn deliberately:

- **CALC states what a body spends, not what a plate should hold.** Its output is a
  property of the person — an energy expenditure, and the trajectory a given intake
  implies. It is not a verdict on any food.
- **The number does not travel.** No target is pushed into FOOD SEARCH, no plate is graded
  against it, no progress ring appears over the table. The two apps stay separate, and the
  table keeps stating what is on the plate.
- **The output is a curve, not a permission.** The honest thing a calculator can say is
  "hold this and here is where it goes, and here is how long". It cannot say what anyone
  should weigh, and it will not try.

Everything below is arithmetic on public data, the same as the rest of the site. It is not
advice, and the app has to say so somewhere a person will actually read it — the game's
caveat sits behind a mark at the end because that is when it lands; CALC's belongs on the
result, for the same reason.

**Guard rails, decided up front:**

- The control is a **calorie slider**, not a goal. Nobody types a target weight or a target
  body fat, so the app never has to hold an opinion about either. It answers only "hold
  this and here is where it goes".
- The slider has a floor: it will not travel below 1,500 kcal/day for men or 1,200 for
  women. It stops there and says why rather than refusing silently.
- Past about 1% of body weight per week the slider enters a marked zone (see §3). It is not
  blocked — faster is possible — but the lean band on the chart is doing the arguing, which
  is better than a warning nobody reads.
- The body render stops at essential fat — roughly 3–5% for men and 8–12% for women (ACSM).
  There is no asset below it and the slider will not drive the model there.
- No BMI target, no "ideal weight", no goal weight field.
- Under-18 is out of scope and the app says so rather than guessing.

---

## 1. The three layers

| Layer | Question | Model | Shown as |
|---|---|---|---|
| Maintenance | What does this body spend in a day? | RMR equation × lifestyle PAL, plus training priced in METs | one number |
| Fat curve | Hold an intake — where does weight go, and when? | Dynamic energy balance, not 3,500 kcal/lb | the rotating body, and body fat % |
| Lean curve | How much of that change is fat and how much is not? | Forbes partitioning, modified by protein and training | the chart behind the mark |

Each layer needs strictly more from the user than the last, which sets the screen order. But
the *output* order is inverted: the body comes first and the arithmetic is behind a mark,
because the person who needs the arithmetic will go looking and the person who does not
should never have to see it.

---

## 2. Maintenance

### Parameters, in order of how much they buy

1. **Sex** — separate coefficients in every equation worth using.
2. **Age** — RMR falls with age in every equation; the coefficient is about −5 kcal/year.
3. **Height**
4. **Weight**
5. **Daily life** — how the day is spent, *not counting training*. See below.
6. **Training** — sessions, length and intensity, priced separately. See below.

**Body fat % is not asked for.** It is derived (§4), shown as an output, and correctable by
anyone who knows theirs. That is the single biggest change from a conventional calculator:
the number people are worst at estimating, and least comfortable being asked for, is the
one the app hands *back* to them.

### RMR

**Default: Mifflin–St Jeor (1990).**

```
RMR (men)   = 10·W(kg) + 6.25·H(cm) − 5·A(y) + 5
RMR (women) = 10·W(kg) + 6.25·H(cm) − 5·A(y) − 161
```

Derived on 498 healthy adults, normal weight and obese, by indirect calorimetry.
[Mifflin MD, St Jeor ST, Hill LA, Scott BJ, Daugherty SA, Koh YO. *A new predictive
equation for resting energy expenditure in healthy individuals.* Am J Clin Nutr.
1990;51(2):241–247.](https://ajcn.nutrition.org/article/S0002-9165(23)16698-6/fulltext)

Chosen because a systematic review for the Academy of Nutrition and Dietetics found it
the most reliable of the major equations, predicting RMR within 10% of measured in more
non-obese and obese individuals than any other, with the narrowest error range.
[Frankenfield D, Roth-Yousey L, Compher C. *Comparison of predictive equations for resting
metabolic rate in healthy nonobese and obese adults: a systematic
review.* J Am Diet Assoc. 2005;105(5):775–789.](https://www.jandonline.org/article/S0002-8223(05)00149-5/abstract)

**When body fat % is known: Katch–McArdle / Cunningham,** on lean body mass:

```
LBM  = W × (1 − BF%)
RMR  = 370 + 21.6·LBM(kg)          (Katch–McArdle)
RMR  = 500 + 22·LBM(kg)            (Cunningham 1980)
```

Cunningham JJ. *A reanalysis of the factors influencing basal metabolic rate in normal
adults.* Am J Clin Nutr. 1980;33(11):2372–2374. These beat Mifflin at the extremes — the
very lean and the very muscular — precisely where a weight-only equation is worst, since
they are reading the tissue that actually respires.

**Not used, and why:** Harris–Benedict (1919, rev. Roza & Shizgal 1984) overestimates by
about 5% in modern populations, and is kept only as a comparison line if the app ever shows
one. Schofield (1985) is the FAO/WHO/UNU basis and the Oxford revision (Henry 2005) is its
successor — both are defensible and worth holding as alternates behind the same interface.

### Activity, in two questions

One five-way "activity level" dropdown is the worst control in every calorie calculator
ever built. It asks a person to average their whole life into one adjective, it silently
mixes two quite different things, and everybody picks one band too high. It splits cleanly:

**Question A — the day you spend anyway.** Desk, on your feet, or physical work. This is
NEAT plus occupational activity, it is by far the larger of the two for most people, and it
is the one nobody thinks to count. Priced as a baseline PAL on the FAO/WHO/UNU bands:

| Category | PAL |
|---|---|
| Sedentary / light activity lifestyle | 1.40 – 1.69 |
| Moderately active | 1.70 – 1.99 |
| Vigorously active | 2.00 – 2.40 |

FAO/WHO/UNU. *Human Energy Requirements.* Report of a Joint Expert Consultation, Rome,
2001 (published 2004).

**Worth stating plainly in the app:** the 1.2 "sedentary" multiplier that almost every
online calculator uses is *below* the FAO floor of 1.40 for a sedentary lifestyle. It is a
Harris–Benedict-era convention, not a measured category, and it is one reason calculators
read low. The app uses the FAO bands.

**Question B — the training you choose.** Sessions per week × minutes × how hard. Priced
in METs rather than adjectives, which is what makes an explainer possible: a MET is a
multiple of resting metabolism, so the app can say what each option *is* rather than what
it is called.

```
kcal per session ≈ (MET − 1) × weight(kg) × hours
```

The −1 matters and is usually dropped: resting metabolism is already counted in the RMR, so
charging the full MET double-counts an hour of being alive. Over a year of training that is
not a rounding error.

Indicative values, all from the Compendium:

| Intensity | Looks like | MET |
|---|---|---|
| Light | Walking, easy cycling, yoga | 2.5 – 3.5 |
| Moderate | Brisk walking, weights with rest, doubles tennis | 4 – 6 |
| Vigorous | Running, circuits, hard cycling, singles | 7 – 10 |
| Very hard | Intervals, sprints, competitive sport | 10 – 14 |

[Ainsworth BE, Haskell WL, Herrmann SD, et al. *2011 Compendium of Physical Activities: a
second update of codes and MET values.* Med Sci Sports Exerc.
2011;43(8):1575–1581.](https://pubmed.ncbi.nlm.nih.gov/21681120/) — now superseded by the
[2024 Adult Compendium](https://www.sciencedirect.com/science/article/pii/S2095254623001084),
which is the one to cite and to take values from.

**Two traps this split creates, both worth handling:**

1. **Double counting.** If Question A's band already includes training, adding Question B on
   top counts it twice. So Question A must say *"not counting exercise"* on the screen, in
   those words, and its bands must be read as lifestyle-only.
2. **Exercise does not add linearly.** Total energy expenditure plateaus above moderate
   activity rather than rising with it — more active populations do not spend proportionally
   more. [Pontzer H, Durazo-Arvizu R, Dugas LR, et al. *Constrained total energy expenditure
   and metabolic adaptation to physical activity in adult humans.* Curr Biol.
   2016;26(3):410–417.](https://pubmed.ncbi.nlm.nih.gov/26832439/) A calculator that adds
   every session at face value overestimates, and overestimating maintenance is exactly how
   people end up eating at maintenance while believing they are in a deficit. v1 should at
   minimum say this on the result; a compensation factor on high training volumes is the
   better answer and needs a decision (§7).

The 2023 DRI update reorganised this into four categories — inactive, low active, active,
very active — set at approximate quartiles of the PAL distribution in doubly-labelled-water
studies, and, importantly, **predicts total energy expenditure directly** from age, height,
weight and category rather than going through a BMR equation and a multiplier. That is the
better model and the more current citation:
[National Academies of Sciences, Engineering, and Medicine. *Dietary Reference Intakes for
Energy.* Washington, DC: The National Academies Press,
2023.](https://www.nationalacademies.org/publications/26818)

> **To do before implementing:** the 2023 EER coefficients must be transcribed from the
> report itself. They are not the 2005 IOM equations, and the 2005 ones are what every
> secondary source returns when you search for them. Do not take them from a calculator
> site.

### Thermic effect of food

About 10% of intake at a mixed diet, but it is macro-dependent — roughly 20–30% of protein
calories, 5–10% of carbohydrate, 0–3% of fat. The site already knows the macro split of a
plate, so if CALC ever reads a plate from FOOD SEARCH this is the one place the two could
honestly meet. Until then, 10% folded into the PAL is fine and is what the PAL bands
already assume.

---

## 3. The fat curve

### What not to do

**The 3,500 kcal per pound rule is wrong**, and this is the single most important thing the
app gets right that its competitors get wrong. It comes from
Wishnofsky M. *Caloric equivalents of gained or lost weight.* Am J Clin Nutr.
1958;6(5):542–546 — a static calculation, correct only as the energy content of a pound of
adipose tissue, and wrong the moment it is used to predict a trajectory. Applied
dynamically it assumes energy balance never changes, and so **overestimates weight loss,
increasingly with time**.

[Hall KD, Chow CC. *Why is the 3500 kcal per pound weight loss rule wrong?* Int J Obes.
2013;37(12):1614.](https://www.nature.com/articles/ijo2013112) —
and the article that prompted it, Thomas DM et al. *Can a weight loss of one pound a week
be achieved with a 3500-kcal deficit?* J Acad Nutr Diet. 2014;114(6):857–861.

Two things break it:

1. **A lighter body spends less.** RMR falls as mass falls, so the deficit closes itself.
2. **Adaptive thermogenesis.** Expenditure falls *beyond* what the new body composition
   predicts. Rosenbaum M, Leibel RL. *Adaptive thermogenesis in humans.* Int J Obes.
   2010;34 Suppl 1:S47–55; and the classic Leibel RL, Rosenbaum M, Hirsch J. *Changes in
   energy expenditure resulting from altered body weight.* N Engl J Med.
   1995;332(10):621–628.

### What to do

Dynamic energy balance: a two-compartment model where the deficit is applied against a
maintenance that is itself recomputed as the body changes.

[Hall KD, Sacks G, Chandramohan D, Chow CC, Wang YC, Gortmaker SL, Swinburn BA.
*Quantification of the effect of energy imbalance on bodyweight.* Lancet.
2011;378(9793):826–837.](https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(11)60812-X/abstract)
— the paper behind the [NIH Body Weight Planner](https://www.niddk.nih.gov/bwp).

Its own rule of thumb, for an average overweight adult, is the honest headline number and
should probably be a line of copy in the app:

> every change of energy intake of 100 kJ/day leads to an eventual bodyweight change of
> about 1 kg — equivalently **about 10 kcal/day per pound** — with **half** the change
> reached in **about 1 year** and **95%** in **about 3 years**.

Two consequences the app should show rather than state:

- The curve **flattens**. A 500 kcal deficit does not produce a straight line; it produces
  something asymptotic. Drawing that is the whole point.
- **Adults with more body fat lose more for the same deficit, and take longer to settle.**

Energy densities for the two compartments — roughly 9,400 kcal/kg for fat tissue and
1,800 kcal/kg for fat-free tissue — are what convert an energy imbalance into a mass
change. *These two constants must be transcribed from Hall 2011 (or the model's supplement)
before use; they are quoted inconsistently in secondary sources.*

### Rate

Capped at **0.5–1.0% of body weight per week**, and the cap is evidence, not caution:

[Garthe I, Raastad T, Refsnes PE, Koivisto A, Sundgot-Borgen J. *Effect of two different
weight-loss rates on body composition and strength and power-related performance in elite
athletes.* Int J Sport Nutr Exerc Metab. 2011;21(2):97–104.](https://journals.humankinetics.com/view/journals/ijsnem/21/2/article-p97.xml)
— 24 elite athletes, all resistance training four times a week, randomised to 0.7%/week or
1.4%/week. **Lean body mass rose 2.1% in the slow group and did not change in the fast
group.** Same training, same athletes, same direction of travel: the rate alone decided
whether lean mass came along.

Helms ER, Aragon AA, Fitschen PJ. *Evidence-based recommendations for natural bodybuilding
contest preparation: nutrition and supplementation.* J Int Soc Sports Nutr. 2014;11:20 —
0.5–1%/week, the same window from the applied side.

---

## 4. The lean curve

This is the part almost no calculator draws, and it is the part that makes CALC worth
building. It is also the layer the whole interface now hangs off, because body fat has been
promoted from an input to the headline output.

### Where the starting body fat comes from

Forbes needs a fat mass to start from, and the app has decided not to ask for one. It is
derived from what has already been collected — sex, age, height, weight:

```
BF%  =  1.20·BMI  +  0.23·age  −  10.8·(1 if male else 0)  −  5.4
```

Deurenberg P, Weststrate JA, Seidell JC. *Body mass index as a measure of body fatness:
age- and sex-specific prediction formulas.* Br J Nutr. 1991;65(2):105–114.

This is a population estimate and must be labelled as one — it reads high on the muscular
and low on the sedentary-thin, which is the same failure BMI has, for the same reason.
Three consequences for the design:

- The estimate is **shown, not hidden**: "we are assuming about 24% — tap to change". A
  wrong number a person can see and correct is far better than a wrong number buried in the
  model, and this turns the least answerable question in the app into a confirmation rather
  than a demand.
- Anyone who *does* know theirs — a DEXA, a decent scale, calipers — corrects it in one tap
  and the whole model sharpens, including the RMR (which switches to Katch–McArdle on lean
  mass, §2).
- The tape-measure path (Navy circumference, Hodgdon & Beckett 1984) sits behind the same
  control for anyone willing to fetch a tape. It is meaningfully better than Deurenberg and
  meaningfully worse than a scan.

Because the *change* in body fat is driven by Forbes from the starting fat mass, an error in
the starting estimate shifts the whole trajectory rather than distorting its shape. The
curve's shape — the flattening, the lean share — survives a bad estimate. Its absolute
position does not. Say that on the chart.

### Forbes

Fat-free mass and fat mass are not independent. Across a large body of composition data,
Forbes found:

```
F = D · exp(L / 10.4)          F = fat mass (kg), L = lean mass (kg)
```

Differentiating gives the fraction of a weight change that comes from fat-free mass, as a
function of the fat mass you start with:

```
ΔFFM / ΔBW  =  10.4 / (10.4 + FM)
```

Forbes GB. *Lean body mass–body fat interrelationships in humans.* Nutr Rev.
1987;45(8):225–231; and Forbes GB. *Body fat content influences the body composition
response to nutrition and exercise.* Ann N Y Acad Sci. 2000;904:359–365. Re-derived and
validated in
[Hall KD. *Body fat and fat-free mass inter-relationships: Forbes's theory revisited.*
Br J Nutr. 2007;97(6):1059–1063.](https://www.cambridge.org/core/journals/british-journal-of-nutrition/article/body-fat-and-fatfree-mass-interrelationships-forbess-theory-revisited/E4058619DF9042AB22DF2CF7B0A88152)

What it says, in the app's own terms:

| Starting fat mass | Share of weight lost that is *not* fat |
|---|---|
| 8 kg (very lean) | 57% |
| 15 kg | 41% |
| 25 kg | 29% |
| 40 kg | 21% |

**The leaner you are, the more of each pound is muscle.** That single sentence is the
reason a fat-loss calculator has to ask for body fat, and the reason the same deficit is a
different proposition for two different people at the same weight. It is also, drawn, the
most interesting picture on the site after the donut.

### What moves the curve

Forbes gives the baseline; three things shift it, and each is a switch the app can offer:

- **Protein.** 1.6 g/kg/day is the breakpoint above which supplementation adds nothing
  further to resistance-training gains in fat-free mass (95% CI 1.03–2.20).
  [Morton RW et al. *A systematic review, meta-analysis and meta-regression of the effect of
  protein supplementation on resistance training-induced gains in muscle mass and strength
  in healthy adults.* Br J Sports Med. 2018;52(6):376–384.](https://pubmed.ncbi.nlm.nih.gov/28698222/)
  In a deficit the requirement is higher — Helms ER, Zinn C, Rowlands DS, Brown SR. *A
  systematic review of dietary protein during caloric restriction in resistance trained lean
  athletes.* Int J Sport Nutr Exerc Metab. 2014;24(2):127–138 — 2.3–3.1 g/kg of **fat-free
  mass**, which is a different denominator and worth stating as such.
- **Resistance training.** Cava E, Yeat NC, Mittendorfer B. *Preserving healthy muscle
  during weight loss.* Adv Nutr. 2017;8(3):511–519.
- **Rate.** Garthe, above.

### The gain side

Symmetric in form, much less certain in magnitude. Partitioning of a surplus varies
enormously between people: Bouchard C et al. *The response to long-term overfeeding in
identical twins.* N Engl J Med. 1990;322(21):1477–1482 fed twelve pairs of twins 1,000
kcal/day over maintenance for 100 days — the variance *between* pairs was several times the
variance *within* them. The app should show a band, not a line, on the gain side, and say
why.

Applied guidance: a 10–20% surplus, 0.25–0.5% body weight per week. Iraki J, Fitschen P,
Espinar S, Helms E. *Nutrition recommendations for bodybuilders in the off-season: a
narrative review.* Sports (Basel). 2019;7(7):154.

---

## 5. The body

**Built, as a morph-target glTF blended in Three.js. The mesh shipping today is a
placeholder; the pipeline around it is real.**

### Why not sprite sheets, and why not a generative model

The earlier plan here was 17 sprite sheets of 24 frames, cross-faded. Baked morph
targets beat it on every axis that matters: one file instead of seventeen, ~145 KB instead
of several megabytes, *continuous* blending instead of 5% steps, and rotation that is
actually rotation rather than a flipbook — so the four things the sprite plan had to
guarantee by hand (identical camera, pose, lighting, frame anchoring) are guaranteed by
construction, because it is one mesh with one number changed.

Generative video was never the tool. The requirement is one parameter varying with
everything else identical, and diffusion drifts on identity, pose, lighting and framing at
once; seventeen generations would be seventeen different people, and "24% body fat" is not
something a prompt can be calibrated against.

### The contract

`tools/build_body_glb.py` writes the placeholder and documents the contract; `body.js`
reads nothing else, so any replacement that honours it drops in without a code change:

  * one mesh, one primitive, POSITION + NORMAL, indexed triangles
  * the **base mesh is the leanest** level
  * N morph targets in **ascending** order of body fat, each with POSITION and NORMAL deltas
  * `mesh.extras.bodyFat` lists the body-fat percentage of the base and of every target,
    in order — the runtime builds its blend from that and needs to know nothing else
  * Y up, metres, feet at y=0, facing +Z

### The blend

One parameter swept across N shapes, so each target's influence is a hat function on the
level axis. That makes the result exactly the linear interpolation between the two shapes
either side and nothing else — and because the deltas are measured from the base rather
than from each other, only those two are ever non-zero.

### The real bake

`tools/mblab_bake.py` — MB-Lab (AGPL, Blender 4.x) for the bodies, then Blender for the
part that must be exact. You build one character per fat level with **only the body-mass
slider moved**, finalize each, and name them `bf8`, `bf15` and so on; the script joins them
onto the leanest as shape keys, decimates to about 6,000 triangles, writes the body-fat
list into the mesh's custom properties and exports the .glb. It refuses to run if the
levels differ in vertex count, because `join_shapes` maps by index and the failure is
silent otherwise.

### Handling it

Pointer events with a Map keyed by `pointerId`, so a mouse, one finger and two
fingers all take the same path. One pointer spins it, with momentum. Two pinch it,
between 0.8x and 2.4x — and zoomed in, a vertical drag walks the camera up and down
the body, clamped to its own extent, because a centred zoom otherwise just parks you on
the hips. A wheel zooms on a desktop. The canvas carries `touch-action: none` so the
browser hands the gesture over intact, and the page cannot scroll under it anyway.

### What the runtime does

Three (670 KB) and GLTFLoader are **vendored into `vendor/three/`** rather than fetched from
a CDN — the site serves everything but React from its own origin — and are **dynamically
imported the first time CALC is opened**, so nobody who came for the food table pays for
them. WebGL failure or a model that will not load falls back to the line drawing.

The figure rotates slowly on its own, takes a drag with momentum, and holds still under
`prefers-reduced-motion`. On the result screen it is driven by the scrubbed trajectory, so
dragging through the year *is* the animation.

### Still to do

* The real MB-Lab bake. The placeholder is a lofted stack of rings — it reads as a standing
  figure and the change reads clearly, but it is nobody's body. Its tubes *intersect* rather
  than join, so a seam shows where the legs meet the pelvis; a single continuous surface out
  of MB-Lab will not have one.
* One axis only, still: body fat. Lean mass rides on the chart. See the argument in §5 of
  the earlier plan, which still holds.

## 6. Mobile screens

**Four steps, not seven.** Sex, age, height and weight are all the same question — who is
this — and splitting them made a seven-step run out of what is really one form.

```
LAUNCHER
  └─ CALORIE CALC
       │
       1  YOU        sex side by side, then age, height and weight, each
       │             with a slider AND a number box, both live. A slider is
       │             faster and a number is exact; there is no reason to
       │             make anyone choose. Minimum age 18.
       2  BODY FAT   a slider, opening on the Deurenberg estimate, with the
       │             figure above it. No number box: nobody knows their body
       │             fat to the percent, and a field that invites a typed
       │             figure implies a precision that does not exist.
       3  YOUR DAY   three tiles, and "not counting exercise" said out loud
       4  TRAINING   sessions, minutes, and how hard, in METs with examples
       └─ 5  RESULT
```

**The figure is on every screen**, not just the last. It is the constant the whole app is
about, it fills the space a phone screen otherwise leaves empty under a short question, and
it means the payoff is visible from step one rather than being a surprise at the end. On
the body-fat step it is the control's own readout.

### The result screen

This is the app. Everything above it is data entry.

```
┌──────────────────────────────┐
│  MAINTENANCE  2,480 kcal     │   the number the app exists to produce
│                              │
│         [ rotating body ]    │   drag to spin
│                              │
│   24.1%  ──────────▶ 19.4%   │   body fat, now → at the scrubbed date
│   82.0 kg ─────────▶ 74.6 kg │   weight, secondary
│                              │
│  ●───────────────────────    │   TIME     ◀ 0 ── 3 ── 6 ── 12 months
│  ────────●───────────────    │   INTAKE   ◀ 1,500 ─────── 3,200 kcal
│                              │
│  [ i ]              [ ⌥ ]    │   caveat            the curves
└──────────────────────────────┘
```

Two sliders, and the inversion is the whole idea: **the input is calories and the output is
a body**, rather than the input being a goal and the output a calorie number. Nobody has to
name a target. Move the intake slider and the figure, the percentage and the date all
answer. Move the time slider and the year plays.

Three things that fall out of this for free, all of which conventional calculators struggle
with:

- **The flattening is felt rather than explained.** Drag time to 12 months and the second
  six months plainly does less than the first. That is §3's whole point, delivered without a
  paragraph.
- **No goal pressure.** There is no field in which to type an aspiration, so the app never
  has to have an opinion about one.
- **The floor is a physical stop.** The slider will not go below 1,200/1,500 and the marked
  zone past 1%/week is a stripe on the track, not a modal.

### The curves, behind a mark

The `⌥` opens what §4 actually computed, for anyone who wants it. Same device as the game's
caveat: out of the way, one tap, no cost to the person who does not care.

- Weight, fat mass and lean mass on one time axis, in the donut's own colours.
- **Maintenance falling over the same axis** — the line nobody shows and everybody needs,
  because it is why month twelve is not month one.
- The Forbes partition as a live figure: "at your body fat, about **34%** of each kilogram
  lost is not fat" — recomputed as the trajectory runs, since it changes as fat mass falls.
- The equations and citations, named. The people who open this panel are exactly the people
  who will want to check the arithmetic, and the site has never been shy about showing its
  working.

---

## 7. Deliberately not doing

- No goal weight, no BMI target, no "ideal" anything.
- No micronutrient or health scoring — the site does not rate food and will not start.
- No account, no history, no weigh-in log. It computes; it does not track. (`localStorage`
  for the last inputs only, as the plate already does.)
- No target pushed into FOOD SEARCH.
- No claim of precision the model does not have: every prediction equation here has an
  error band of roughly ±10% at the individual level, and the app should say so on the
  result rather than in a footnote.

---

## 8. Open questions

**Blocking the body assets** (needed before anything is rendered) — this is the whole of
what is left, and the placeholder is deliberately unlovely so it is not mistaken for done:

- **Style** — photoreal or stylised? Stylised is cheaper, fits the site, and is the
  recommendation, but it is a one-way door once 17 sheets exist.
- **Raster or vector** — sprite sheets, or SVG contours with matched point counts that the
  app can genuinely morph between? One experiment answers it.
- **Band resolution** — 5% steps with a cross-fade, or 2.5% for a smoother run at twice the
  assets?
- **Does the figure need a build axis after all?** The one-axis argument in §5 is good but
  it is an argument, not a test. Worth putting two bands in front of someone at 60 kg and
  100 kg before committing.

**Shipped, with a note against each:**

- The model runs Mifflin—St Jeor, or Katch—McArdle the moment a body fat is picked; the FAO
  lifestyle bands read at their exercise-free end; training at `(MET − 1) × kg × hours`;
  Forbes partitioning against a maintenance recomputed daily; and adaptive thermogenesis as
  10% of the deficit, scaled to its depth and ramped in over eight weeks.
- **It was checked against Hall's published rule of thumb and lands on it.** A 100 kcal/day
  deficit on an 80 kg body gives **2.7 kg at one year and 4.3 kg at three** — against Hall's
  "about 1 kg per 100 kJ/day, half in a year, 95% in three", which is 2.2 kg and 4.5 kg.
  The shape and the asymptote are both right. That check should be re-run whenever the
  adaptation term is touched.
- Metric only for now. Imperial is a real gap, not a decision.

**Still blocking the model:**

- The 2023 DRI EER coefficients, which have to come off the report itself (§2).
- Hall's two compartment energy densities, same problem (§3). The 9,400 / 1,800 kcal/kg
  currently in the code are the widely-quoted values and produce the right answer against
  the rule of thumb above, but they are not yet read from source.
- **Whether to apply a compensation factor for training volume** (Pontzer, §2). Doing
  nothing overestimates maintenance for heavy trainers, which is the failure mode that
  matters most. Doing something means picking a factor the literature does not hand over
  cleanly. Leaning towards: v1 says it on the result, v2 models it.

**Design, decidable later:**

- Does the intake slider default to maintenance, or to something below it? Maintenance is
  the neutral answer and probably right — the app opens by telling you what you spend, and
  moving from there is the user's move, not the app's.
- Metric/imperial: does it follow the food table's 100 G / OZ toggle, or is it its own
  setting? Probably the former, since it is the same reader.
- Does the whole seven-step run persist in `localStorage`, so a return visit lands on the
  result with a change link? Almost certainly yes — the plate already does this — but it
  needs to not become a tracker (§7).
