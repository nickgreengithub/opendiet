# Calorie calc — plan

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

- No target below 1,500 kcal/day for men or 1,200 for women is ever *produced* by the
  app. If the requested rate demands one, the app shows the rate it can support instead
  and says why.
- Rate is capped at 1% of body weight per week (see §3), not because faster is impossible
  but because faster costs lean mass and the app can show that it does.
- No BMI target, no "ideal weight", no goal weight field. The input is a *rate*; the
  output is a *curve*. A person who wants a destination can read one off the curve.
- Under-18 is out of scope and the app says so rather than guessing.

---

## 1. The three layers

| Layer | Question | Model |
|---|---|---|
| Maintenance | What does this body spend in a day? | RMR equation × activity, or a DLW-based TEE equation |
| Fat curve | Hold an intake — where does weight go, and when? | Dynamic energy balance, not 3,500 kcal/lb |
| Lean curve | How much of that change is fat and how much is not? | Forbes partitioning, modified by protein and training |

Each layer needs strictly more from the user than the last. That is the screen order.

---

## 2. Maintenance

### Parameters, in order of how much they buy

1. **Sex** — separate coefficients in every equation worth using.
2. **Age** — RMR falls with age in every equation; the coefficient is about −5 kcal/year.
3. **Height**
4. **Weight**
5. **Activity level (PAL)** — the largest single lever after body size, and the one the
   user is worst at estimating.
6. **Body fat %** *(optional)* — unlocks the lean-mass equations and, more importantly,
   the Forbes curve in §4. Without it the app can still run, on a population estimate.

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

### Activity

RMR × PAL. The FAO/WHO/UNU categories are the quotable ones:

| Category | PAL |
|---|---|
| Sedentary / light activity lifestyle | 1.40 – 1.69 |
| Moderately active | 1.70 – 1.99 |
| Vigorously active | 2.00 – 2.40 |

FAO/WHO/UNU. *Human Energy Requirements.* Report of a Joint Expert Consultation, Rome,
2001 (published 2004).

**Worth stating plainly in the app:** the 1.2 "sedentary" multiplier that almost every
online calculator uses is *below* the FAO floor of 1.40 for a sedentary lifestyle. It is a
Harris–Benedict-era convention, not a measured category, and it is one of the reasons
calculators read low. The app uses the FAO bands.

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
building.

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

## 5. Mobile screens

The game's idiom, not the table's: one question per screen, big targets, nothing scrolls
inside a step, and the whole thing is over in under a minute. The table's idiom — every
number at once — is for the result, not for the questions.

```
LAUNCHER
  └─ CALORIE CALC
       │
       1  YOU          sex · age · height · weight          (steppers, not a keyboard,
       │                                                     where a stepper will do)
       2  ACTIVITY     four tiles, FAO bands, each with
       │               one line of what it actually means
       │               in hours and days, not adjectives
       3  BODY FAT     optional, and said to be optional.
       │               Three ways in: skip · estimate from
       │               height/weight/age · type a known figure
       4  GOAL         lose fat · hold · gain
       5  RATE         a slider in %/week, hard-stopped at
       │               the cap, reading out kcal/day and a date
       └─ 6  RESULT
```

**The result screen** is the showpiece and should be drawn, not listed — the same principle
as opening a food:

- The number, large: maintenance, and the target beside it.
- **The curve.** Weight against time, out to a year, with fat mass and lean mass as two
  bands stacked inside it. The flattening is visible. The lean band is visible. Nobody else
  draws this.
- Under it, in the table's language: the split at 3, 6 and 12 months — kg of fat, kg of
  lean, and the maintenance the body will have *then*, which is the number that surprises
  people.
- The caveat, at the end, behind a mark, as in the game.

**Reuse, not reinvention:** the donut's ring geometry and its colour language, the game's
card and tile idiom, the amount steppers from the food detail, the 100 G / OZ toggle
pattern for metric/imperial, `gResults`'s grade-header layout for the result header.

---

## 6. Deliberately not doing

- No goal weight, no BMI target, no "ideal" anything.
- No micronutrient or health scoring — the site does not rate food and will not start.
- No account, no history, no weigh-in log. It computes; it does not track. (`localStorage`
  for the last inputs only, as the plate already does.)
- No target pushed into FOOD SEARCH.
- No claim of precision the model does not have: every prediction equation here has an
  error band of roughly ±10% at the individual level, and the app should say so on the
  result rather than in a footnote.

---

## 7. Open questions

- Which maintenance model ships as the default: Mifflin × FAO PAL (well understood, easy to
  cite, two-step) or the 2023 DRI TEE equations (one step, DLW-based, current)? Leaning
  DRI-first with Mifflin as the fallback when a category is ambiguous — but the coefficients
  have to be read from the report before deciding.
- Body fat estimation when the user does not know theirs: Deurenberg's BMI-based formula
  (Br J Nutr. 1991;65(2):105–114) is one line and honest about being a population estimate;
  the Navy circumference method (Hodgdon & Beckett, 1984) is better but wants a tape
  measure. Possibly both, with the tape measure as the "if you have one" path.
- Does the curve animate as the rate slider moves, or settle after? The former is the
  site's instinct and the more expensive to make smooth.
