# Food libraries

Static JSON, loaded by `index.html` at runtime by relative path. Nothing here is
built when the site is served — these files are committed as-is.

| File | Library | Foods | Source |
|---|---|---|---|
| `core.json` | CORE | 1,779 | SR Legacy, whole-food groups only, generic (unbranded) descriptions |
| `legacy.json` | SR LEGACY | 7,756 | USDA FoodData Central, SR Legacy release 2019-04-02 |
| `survey.json` | SURVEY FNDDS | 8,661 | USDA FoodData Central, Survey (FNDDS) release 2020-03-31 |

USDA FoodData Central is public domain (17 U.S.C. §105).

## Shape

```json
{"cats": ["DAIRY", "FRUIT", "..."],
 "foods": [["Broccoli, raw", 7, 34, 2.8, 6.6, 2.6, 0.4, 0.1, 1.7, 0]]}
```

Each food is `[name, catIndex, kcal, protein, carb, fibre, fat, satFat, sugar, liquid]`,
optionally followed by `everyday`, then `servingGrams, servingLabel`:

```json
["Apples, raw, with skin", 7, 52, 0.3, 13.8, 2.4, 0.2, 0, 10.4, 0, 1, 182, "MEDIUM"]
```

Grams per 100 g, except where `liquid` is `1` — those are per 100 ml. A food with no
reported value for a nutrient carries `0`, and the table shows it as `0`.

`everyday` marks the entry a shopper means by the plain word — written by
[`../tools/mark_common.py`](../tools/mark_common.py), used only to order search results.
`servingGrams` and `servingLabel` are a second way of reading the amount, written by
[`../tools/add_portions.py`](../tools/add_portions.py). Where FDC publishes a household
measure it is used — `182 g = 1 MEDIUM`, `29 g = 1 SLICE` — which covers 5,805 of SR
Legacy's 7,756 foods and 8,479 of FNDDS's 8,661. The rest fall back to a standard unit,
because for a steak or a handful of cashews the only measure FDC publishes is a weight in
ounces, which is not a thing you can picture: solids get `28.35 g = 1 OZ`, liquids get
`240 ml = 1 CUP`, or `15 ml = 1 TBSP` where FDC's own portion is under 60 ml. Every food
therefore carries a second unit; the fallback is a conversion rather than a serving, which
is how the site reads it — `100 g = 3.5 OZ`. A reader that stops at `liquid` is unaffected
by any of them.

Nutrients are FDC nutrient ids 1008 (energy, kcal), 1003 (protein), 1005 (carbohydrate
by difference), 1079 (fibre), 1004 (total fat), 1258 (saturated fat), 2000 (total sugars).
Foods with no energy value are dropped, which is why the counts sit just under the
release totals (SR Legacy ships 7,793 foods; 37 carry no kcal).

## Categories

SR Legacy carries USDA food-group ids, mapped to the short tokens above. FNDDS has no
food-group id — it carries a WWEIA category code, whose numeric ranges are the group
(1000s dairy, 2000s protein, 3000s mixed dishes, and so on).

## Regenerating

`tools/build_data.py` rebuilds these from the FoodData Central CSV releases. It is a
one-off data step, not part of serving the site; point it at unpacked CSV bundles from
<https://fdc.nal.usda.gov/download-datasets.html> and re-run it.
