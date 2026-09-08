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

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
