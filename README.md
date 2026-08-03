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

- **Search and sort** any column — protein, carbs, fat, calories, or name.
- **Three view bases.** Read macros as grams, as a percentage of the food's own macro energy,
  or as their kcal contribution.
- **Portion sizes.** Measure everything per 100 g/ml, per ounce, per tablespoon or per teaspoon.
  Liquids are measured by volume automatically.
- **Star foods to build a plate.** Starred foods drop into a summary with running totals, and
  their portions can be typed in directly. Saved in your browser, not on a server.
- **A fullness score** per food — a per-calorie index built from macro energy shares, fibre
  density and the sheer bulk a calorie buys.
- **Thermic effect toggle.** Deducts the energy digestion itself costs: 25% of protein calories,
  8% of carbohydrate, 2% of fat.
- **One swappable column** for fibre, saturated fat, sugar, calorie density or the fullness score.

## The data

Three libraries, all from USDA FoodData Central, all committed to this repo as static JSON:

| Library | Foods | Source release |
|---|---|---|
| CORE | 1,779 | SR Legacy, whole-food groups, generic (unbranded) descriptions |
| SR LEGACY | 7,756 | SR Legacy, 2019-04-02 |
| SURVEY FNDDS | 8,661 | Survey (FNDDS), 2020-03-31 |

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
tools/              one-off generators (data build, preview image); not part of the site
```

## Licence

[PolyForm Noncommercial 1.0.0](PolyForm%20NonCommercial%201.0.0.txt).

Free to use, copy, modify and share for any **noncommercial** purpose — personal use, research,
teaching, charitable work. Commercial use needs a separate licence; open an issue if you want one.

This is source-available rather than open source in the OSI sense, since that definition does not
permit a restriction on commercial use.

The USDA data itself carries no such restriction — it is public domain and you can do anything
you like with it.
