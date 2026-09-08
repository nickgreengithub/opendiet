#!/usr/bin/env node
// Node tests for recipe.js. Phase 1: parseRecipe only (no food data needed yet). Phase 2
// adds the stemWord/mkFoods/rankFoods extraction (guarded below against the search results
// index.html produced before the extraction) plus the matcher; Phase 3 adds gramsFor, all
// against data/aliases.json + data/units.json and the labelled tools/recipes/*.txt fixtures.
"use strict";
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const OD = require(path.join(__dirname, "..", "recipe.js"));
const ROOT = path.join(__dirname, "..");

let pass = 0, fail = 0;
function test(name, fn) {
  try {
    fn();
    pass++;
  } catch (e) {
    fail++;
    console.error(`FAIL ${name}\n      ${e.message}`);
  }
}

function row1(text) {
  const rows = OD.parseRecipe(text);
  assert.strictEqual(rows.length, 1, `expected 1 row, got ${rows.length}`);
  return rows[0];
}

// ---- quantity forms ---------------------------------------------------------------------

test("plain integer", () => {
  const r = row1("2 tbsp olive oil, extra virgin");
  assert.strictEqual(r.kind, "ing");
  assert.strictEqual(r.qty, 2);
  assert.strictEqual(r.unit, "tbsp");
  assert.strictEqual(r.ing, "olive oil");
  assert.ok(r.prep.includes("extra"));
});

test("decimal", () => {
  const r = row1("0.5 cup milk");
  assert.strictEqual(r.qty, 0.5);
  assert.strictEqual(r.unit, "cup");
  assert.strictEqual(r.ing, "milk");
});

test("ascii fraction", () => {
  const r = row1("1/2 cup sugar");
  assert.strictEqual(r.qty, 0.5);
  assert.strictEqual(r.unit, "cup");
});

test("unicode fraction", () => {
  const r = row1("½ cup sugar");
  assert.strictEqual(r.qty, 0.5);
  assert.strictEqual(r.unit, "cup");
});

test("mixed number", () => {
  const r = row1("1 1/2 cups flour");
  assert.strictEqual(r.qty, 1.5);
  assert.strictEqual(r.unit, "cup");
  assert.strictEqual(r.ing, "flour");
});

test("range", () => {
  const r = row1("1-2 onions, diced");
  assert.strictEqual(r.qty, 1.5);
  assert.strictEqual(r.qtyLo, 1);
  assert.strictEqual(r.qtyHi, 2);
  assert.strictEqual(r.ing, "onions");
  assert.ok(r.prep.includes("diced"));
});

test("range with 'to'", () => {
  const r = row1("2 to 3 cloves garlic");
  assert.strictEqual(r.qty, 2.5);
  assert.strictEqual(r.unit, "clove");
});

test("number word", () => {
  const r = row1("two eggs");
  assert.strictEqual(r.qty, 2);
  assert.strictEqual(r.ing, "eggs");
});

test("indefinite quantity word", () => {
  const r = row1("a knob of butter");
  assert.strictEqual(r.qty, 1);
  assert.strictEqual(r.unit, "knob");
  assert.strictEqual(r.ing, "butter");
});

test("multipack mass", () => {
  const r = row1("2x400g tins chopped tomatoes");
  assert.strictEqual(r.qty, 800);
  assert.strictEqual(r.unit, "g");
  assert.strictEqual(r.ing, "chopped tomatoes");
});

test("multipack mass with spaces", () => {
  const r = row1("2 x 400 g tins chopped tomatoes");
  assert.strictEqual(r.qty, 800);
  assert.strictEqual(r.unit, "g");
});

test("parenthetical mass override", () => {
  const r = row1("1 onion (150g), diced");
  assert.strictEqual(r.qty, 150);
  assert.strictEqual(r.unit, "g");
  assert.strictEqual(r.ing, "onion");
  assert.ok(r.prep.includes("diced"));
});

test("juice of", () => {
  const r = row1("juice of 1 lemon");
  assert.strictEqual(r.qty, 1);
  assert.strictEqual(r.ing, "lemon juice");
});

// ---- units --------------------------------------------------------------------------------

test("size word before noun is a unit", () => {
  const r = row1("2 large eggs");
  assert.strictEqual(r.unit, "large");
  assert.strictEqual(r.ing, "eggs");
});

test("size word alone is not a unit", () => {
  const r = row1("2 large");
  assert.strictEqual(r.unit, null);
});

test("tablespoon spellings", () => {
  assert.strictEqual(row1("1 tablespoon honey").unit, "tbsp");
  assert.strictEqual(row1("1 tbsp honey").unit, "tbsp");
  assert.strictEqual(row1("1 tbs honey").unit, "tbsp");
});

test("teaspoon vs tablespoon do not collide", () => {
  const salt = row1("1 tsp salt");
  assert.strictEqual(salt.kind, "zero");
  assert.strictEqual(salt.unit, "tsp");
  assert.strictEqual(salt.qty, 1);
  assert.strictEqual(row1("1 tsp vanilla extract").unit, "tsp");
});

// ---- prep / state / flags ------------------------------------------------------------------

test("state word", () => {
  const r = row1("400g tomatoes, canned");
  assert.strictEqual(r.state, "canned");
});

test("optional flag", () => {
  const r = row1("1 tsp chili flakes (optional)");
  assert.strictEqual(r.flags.opt, true);
});

test("to taste flag on a named ingredient", () => {
  const r = row1("black pepper, to taste");
  assert.strictEqual(r.kind, "zero");
  assert.strictEqual(r.ing, "black pepper");
  assert.strictEqual(r.flags.taste, true);
});

// ---- zero lines -----------------------------------------------------------------------------

test("salt and pepper to taste is a zero line", () => {
  const r = row1("Salt and pepper, to taste");
  assert.strictEqual(r.kind, "zero");
  assert.strictEqual(r.qty, null);
  assert.strictEqual(r.flags.taste, true);
});

test("bare water is a zero line", () => {
  const r = row1("Water");
  assert.strictEqual(r.kind, "zero");
});

// ---- classification -------------------------------------------------------------------------

test("ALL CAPS heading", () => {
  const r = row1("FOR THE SAUCE");
  assert.strictEqual(r.kind, "head");
});

test("For the ... heading", () => {
  const r = row1("For the sauce:");
  assert.strictEqual(r.kind, "head");
  assert.strictEqual(r.ing, "For the sauce");
});

test("Serves N sets servings", () => {
  const rows = OD.parseRecipe("Serves 4");
  assert.strictEqual(rows[0].kind, "head");
  assert.strictEqual(rows[0].servings, 4);
  assert.strictEqual(OD.recipeServings(rows), 4);
});

test("method step is a note", () => {
  const r = row1("Preheat the oven to 200C and grease a 9-inch tin.");
  assert.strictEqual(r.kind, "note");
});

test("long line without leading quantity is a note", () => {
  const r = row1("Mix everything together in a large bowl until well combined and smooth.");
  assert.strictEqual(r.kind, "note");
});

test("blank line", () => {
  const r = row1("");
  assert.strictEqual(r.kind, "blank");
});

test("bullet and numbering are stripped", () => {
  assert.strictEqual(row1("- 2 eggs").ing, "eggs");
  assert.strictEqual(row1("1. 2 eggs").ing, "eggs");
});

// ---- multi-line recipe end to end -----------------------------------------------------------

test("a small real recipe parses into the right kinds", () => {
  const text = [
    "Serves 4",
    "FOR THE SAUCE",
    "2 tbsp olive oil",
    "1 onion (150g), diced",
    "2 cloves garlic, crushed",
    "1-2 tsp chili flakes (optional)",
    "2x400g tins chopped tomatoes",
    "Salt and pepper, to taste",
    "",
    "Heat the oil in a pan and fry the onion until soft.",
  ].join("\n");
  const rows = OD.parseRecipe(text);
  const kinds = rows.map((r) => r.kind);
  assert.deepStrictEqual(kinds,
    ["head", "head", "ing", "ing", "ing", "ing", "ing", "zero", "blank", "note"]);
  assert.strictEqual(OD.recipeServings(rows), 4);
});

// ---- search extraction (stemWord/mkFoods/rankFoods) --------------------------------------
// Same top results index.html's search produced before stemWord, mkFood and the inline
// scorer moved out of it and into OD.stemWord/OD.mkFoods/OD.rankFoods — the extraction this
// guards was checked byte-for-byte against the pre-extraction code across all three
// libraries and 600+ fuzz queries; these three pin the result so a future change to the
// scorer notices if it moves.
function topNames(list, q, n) {
  const ranked = OD.rankFoods(list.slice(), q);
  ranked.sort((a, b) => (b._hit - a._hit) || (a.name.length - b.name.length) || a.name.localeCompare(b.name));
  return ranked.slice(0, n).map((fo) => fo.name);
}

test("search extraction: same top-6 as before, on real data", () => {
  const d = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "legacy.json"), "utf8"));
  const foods = OD.mkFoods(d);
  assert.deepStrictEqual(topNames(foods, "egg, whole", 6), [
    "Egg, whole · avg",
    "Egg, whole, raw, fresh",
    "Egg, whole, cooked, hard-boiled",
    "Egg, whole, dried",
    "Egg, whole, cooked, fried",
    "Egg, whole, cooked, omelet",
  ]);
  assert.deepStrictEqual(topNames(foods, "kale", 6), [
    "Kale · avg",
    "Kale, raw",
    "Kale, frozen, unprepared",
    "Kale, cooked, boiled, drained, with salt",
    "Kale, cooked, boiled, drained, without salt",
    "Kale, frozen, cooked, boiled, drained, with salt",
  ]);
  assert.deepStrictEqual(topNames(foods, "beef", 6), [
    "Beef, ground · avg",
    "Beef, ground, raw · avg",
    "Beef, loin, separable lean · avg",
    "Beef, New Zealand, imported · avg",
    "Beef, round, separable lean · avg",
    "Beef, brisket, flat half, raw · avg",
  ]);
});

// ---- gramsFor (units) -----------------------------------------------------------------------
const UNITS = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "units.json"), "utf8"));

function line(over) {
  return Object.assign({ qty: 1, qtyText: "1", unit: null, unitText: null, ing: "", flags: {} }, over);
}
function food(over) {
  return Object.assign({ name: "Test food", nl: "test food", cat: "SNACKS" }, over);
}

test("gramsFor: mass unit converts directly", () => {
  const g = OD.gramsFor(line({ qty: 400, qtyText: "400", unit: "g", unitText: "g" }), food(), UNITS);
  assert.strictEqual(g.g, 400);
  assert.strictEqual(g.how, "mass");
});

test("gramsFor: mass unit handles kg", () => {
  const g = OD.gramsFor(line({ qty: 1, unit: "kg", unitText: "kg" }), food(), UNITS);
  assert.strictEqual(g.g, 1000);
});

test("gramsFor: volume prefers the food's own per-portion weight over density", () => {
  const fo = food({ nl: "flour", cat: "GRAINS", pg: 125, pn: "CUP" });
  const cup = OD.gramsFor(line({ qty: 1, unit: "cup", unitText: "cup" }), fo, UNITS);
  assert.strictEqual(cup.g, 125);
  assert.strictEqual(cup.how, "pg");
  // 2 tbsp of the same food scales off its own cup weight, not the generic density table.
  const tbsp = OD.gramsFor(line({ qty: 2, unit: "tbsp", unitText: "tbsp" }), fo, UNITS);
  assert.strictEqual(tbsp.how, "pg");
  assert.ok(Math.abs(tbsp.g - 2 * 125 * (14.7868 / 236.588)) < 0.01);
});

test("gramsFor: volume falls back to density when the food has no per-portion weight", () => {
  const fo = food({ nl: "olive oil", cat: "FATS" });
  const g = OD.gramsFor(line({ qty: 1, unit: "cup", unitText: "cup" }), fo, UNITS);
  assert.strictEqual(g.how, "density");
  // "oil" density word (0.92) wins over the FATS category density (0.92) — same value here,
  // but the point is it used the word table at all, i.e. found a candidate g close to it.
  assert.ok(Math.abs(g.g - 236.588 * 0.92) < 0.01);
});

test("gramsFor: count unit uses the food's own per-count weight when the label matches", () => {
  const fo = food({ nl: "onions, raw", cat: "VEGES", pg: 110, pn: "MEDIUM" });
  const g = OD.gramsFor(line({ qty: 2, unit: "medium", unitText: "medium", ing: "onion" }), fo, UNITS);
  assert.strictEqual(g.g, 220);
  assert.strictEqual(g.how, "count");
});

test("gramsFor: count unit falls back to the ingredient-specific word table", () => {
  const fo = food({ nl: "eggs" });
  const g = OD.gramsFor(line({ qty: 4, unit: "large", unitText: "large", ing: "eggs" }), fo, UNITS);
  assert.strictEqual(g.g, 4 * 50); // count.word.egg.large
});

test("gramsFor: count unit falls back to the generic default", () => {
  const fo = food({ nl: "garlic" });
  const g = OD.gramsFor(line({ qty: 3, unit: "clove", unitText: "clove", ing: "peeled garlic" }), fo, UNITS);
  assert.strictEqual(g.g, 3 * 3); // count.default.clove — no count.word entry for "peeled garlic"
});

test("gramsFor: a bare quantity with no unit is read as 'each'", () => {
  const fo = food({ nl: "onions, raw" });
  const g = OD.gramsFor(line({ qty: 2, unit: null, ing: "onion" }), fo, UNITS);
  assert.strictEqual(g.g, 2 * 110); // count.word.onion.each
  assert.strictEqual(g.how, "count");
});

test("gramsFor: nothing to go on falls back to a default and flags review", () => {
  const toTaste = OD.gramsFor(line({ qty: null, unit: null, flags: { taste: true } }), food(), UNITS);
  assert.strictEqual(toTaste.g, 0);
  assert.strictEqual(toTaste.how, "none");
  assert.strictEqual(toTaste.review, true);

  const noInfo = OD.gramsFor(line({ qty: null, unit: null, flags: {} }), food(), UNITS);
  assert.strictEqual(noInfo.g, 100);
  assert.strictEqual(noInfo.review, true);
});

test("gramsFor: caps at RCP_MAX", () => {
  const g = OD.gramsFor(line({ qty: 50, unit: "kg", unitText: "kg" }), food(), UNITS);
  assert.strictEqual(g.g, 5000);
});

test("gramsFor: no food means no grams, not a guess", () => {
  const g = OD.gramsFor(line({ qty: 400, unit: "g", unitText: "g" }), null, UNITS);
  assert.strictEqual(g.g, 0);
  assert.strictEqual(g.how, "none");
});

// ---- matcher hit rate on labelled real recipes --------------------------------------------
// tools/recipes/*.txt + tools/recipe_expect.json, per RECIPE.md's pass bar: >=85% top-1,
// >=95% top-8. The expect file was generated from a reviewed matchLine run (every line
// checked by hand against the actual food names — see the commit that added it), so this
// test is a regression guard on that review, not a re-derivation of it.
test("matcher: hit rate on labelled recipes clears the pass bar", () => {
  const d = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "legacy.json"), "utf8"));
  const foods = OD.mkFoods(d);
  const aliases = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "aliases.json"), "utf8"));
  const expect = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "recipe_expect.json"), "utf8"));

  const rows = [];
  for (const file of fs.readdirSync(path.join(ROOT, "tools", "recipes")).sort()) {
    const text = fs.readFileSync(path.join(ROOT, "tools", "recipes", file), "utf8");
    rows.push(...OD.parseRecipe(text).filter((r) => r.kind === "ing"));
  }
  assert.strictEqual(rows.length, expect.length,
    `tools/recipes/*.txt parses to ${rows.length} ingredient lines, expect file has ${expect.length} — regenerate recipe_expect.json`);

  let top1 = 0, top8 = 0, gramsOk = 0, gramsChecked = 0;
  rows.forEach((row, i) => {
    const want = expect[i];
    assert.strictEqual(row.raw, want.raw, `line ${i}: recipe text and expect file are out of sync`);
    const m = OD.matchLine(row, foods, aliases);
    if (m.food === want.food) top1++;
    if (want.food === null || m.cands.includes(want.food)) top8++;
    if (want.g) {
      gramsChecked++;
      const fo = foods.find((f) => f.name === want.food);
      const g = OD.gramsFor(row, fo, UNITS);
      if (g.g >= want.g[0] && g.g <= want.g[1]) gramsOk++;
      else console.error(`  grams out of range: "${row.raw}" got ${g.g}, want ${want.g}`);
    }
  });
  const pct = (n, of) => Math.round((100 * n) / of);
  console.log(`  matcher: ${pct(top1, rows.length)}% top-1, ${pct(top8, rows.length)}% top-8 over ${rows.length} lines`);
  console.log(`  grams: ${gramsOk}/${gramsChecked} within range`);
  assert.ok(pct(top1, rows.length) >= 85, `top-1 hit rate ${pct(top1, rows.length)}% is under the 85% bar`);
  assert.ok(pct(top8, rows.length) >= 95, `top-8 hit rate ${pct(top8, rows.length)}% is under the 95% bar`);
  assert.strictEqual(gramsOk, gramsChecked, "some lines resolved grams outside their expected range");
});

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
