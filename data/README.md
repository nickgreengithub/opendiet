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

Each food is `[name, catIndex, kcal, protein, carb, fibre, fat, satFat, sugar, liquid]`.
Grams per 100 g, except where `liquid` is `1` — those are per 100 ml. A food with no
reported value for a nutrient carries `0`, which the table renders as `—`.

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
