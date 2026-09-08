// recipe.js — pasted-recipe parsing and (later) matching/unit conversion.
// A classic script, loaded after support.js in index.html and required directly by node
// under tools/recipe_test.js, so the two never run different code. See RECIPE.md.
"use strict";
(function (root) {

// ---- normalisation --------------------------------------------------------------------

const FRACTION_CHARS = {
  "¼": "1/4", "½": "1/2", "¾": "3/4",
  "⅓": "1/3", "⅔": "2/3",
  "⅕": "1/5", "⅖": "2/5", "⅗": "3/5", "⅘": "4/5",
  "⅙": "1/6", "⅚": "5/6",
  "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8",
};

function normalise(line) {
  let s = line;
  for (const ch in FRACTION_CHARS) s = s.split(ch).join(" " + FRACTION_CHARS[ch]);
  s = s.normalize("NFKC");
  s = s.replace(/^[\s]*[-*•·‣]\s+/, "");        // leading bullet
  s = s.replace(/^[\s]*\d+[.)]\s+/, "");        // leading numbering ("1. ", "1) ")
  s = s.replace(/\s+/g, " ").trim();
  return s;
}

// ---- quantity ---------------------------------------------------------------------------

const NUM_WORDS = {
  a: 1, an: 1, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7,
  eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12, half: 0.5, couple: 2, dozen: 12,
};

// "1", "1.5", "1/2", "1 1/2" (leading whole + fraction)
const NUM_RE = "\\d+\\s+\\d+/\\d+|\\d+/\\d+|\\d+\\.\\d+|\\d+";

function numVal(text) {
  const mixed = text.match(/^(\d+)\s+(\d+)\/(\d+)$/);
  if (mixed) return +mixed[1] + (+mixed[2] / +mixed[3]);
  const frac = text.match(/^(\d+)\/(\d+)$/);
  if (frac) return +frac[1] / +frac[2];
  return parseFloat(text);
}

function takeQty(s) {
  // range: "1-2" / "1 to 2"
  let m = s.match(new RegExp(`^(${NUM_RE})\\s*(?:-|to)\\s*(${NUM_RE})\\b\\s*`, "i"));
  if (m) {
    const lo = numVal(m[1]), hi = numVal(m[2]);
    return { qty: (lo + hi) / 2, qtyLo: lo, qtyHi: hi, qtyText: m[0].trim(), rest: s.slice(m[0].length) };
  }
  // plain number, possibly mixed fraction
  m = s.match(new RegExp(`^(${NUM_RE})\\b\\s*`));
  if (m) {
    const v = numVal(m[1]);
    return { qty: v, qtyLo: v, qtyHi: v, qtyText: m[1], rest: s.slice(m[0].length) };
  }
  // number word ("two eggs", "a pinch")
  m = s.match(/^([a-zA-Z]+)\b\s*/);
  if (m && NUM_WORDS.hasOwnProperty(m[1].toLowerCase())) {
    const v = NUM_WORDS[m[1].toLowerCase()];
    return { qty: v, qtyLo: v, qtyHi: v, qtyText: m[1], rest: s.slice(m[0].length) };
  }
  return null;
}

// ---- units ------------------------------------------------------------------------------

const UNIT_TABLE = {
  g: ["g", "gram", "grams", "gramme", "grammes"],
  kg: ["kg", "kilogram", "kilograms"],
  oz: ["oz", "ounce", "ounces"],
  lb: ["lb", "lbs", "pound", "pounds"],
  ml: ["ml", "milliliter", "milliliters", "millilitre", "millilitres"],
  l: ["l", "liter", "liters", "litre", "litres"],
  tsp: ["tsp", "tsps", "teaspoon", "teaspoons"],
  tbsp: ["tbsp", "tbsps", "tbs", "tablespoon", "tablespoons"],
  cup: ["cup", "cups"],
  floz: ["floz", "fl oz", "fluid ounce", "fluid ounces"],
  pint: ["pint", "pints"],
  clove: ["clove", "cloves"],
  slice: ["slice", "slices", "rasher", "rashers"],
  can: ["can", "cans", "tin", "tins"],
  bunch: ["bunch", "bunches"],
  sprig: ["sprig", "sprigs"],
  head: ["head", "heads"],
  small: ["small"],
  medium: ["medium", "med"],
  large: ["large", "lge"],
  each: ["each"],
  handful: ["handful", "handfuls"],
  pinch: ["pinch", "pinches"],
  dash: ["dash", "dashes"],
  knob: ["knob", "knobs"],
  splash: ["splash", "splashes"],
  drizzle: ["drizzle", "drizzles"],
  sprinkle: ["sprinkle", "sprinkles"],
};
const SIZE_UNITS = new Set(["small", "medium", "large"]);

const UNIT_LOOKUP = {};
for (const key in UNIT_TABLE) for (const spelling of UNIT_TABLE[key]) UNIT_LOOKUP[spelling] = key;
// longest spelling first so "fl oz" beats "fl"
const UNIT_SPELLINGS = Object.keys(UNIT_LOOKUP).sort((a, b) => b.length - a.length);

function takeUnit(s) {
  for (const spelling of UNIT_SPELLINGS) {
    const re = new RegExp("^" + spelling.replace(/\s+/, "\\s+") + "\\b\\.?\\s*", "i");
    const m = s.match(re);
    if (!m) continue;
    const key = UNIT_LOOKUP[spelling];
    if (SIZE_UNITS.has(key)) {
      // a size word is a unit only immediately before a noun, i.e. more text follows
      const remainder = s.slice(m[0].length).trim();
      if (!remainder) continue;
    }
    return { unit: key, unitText: m[0].trim(), rest: s.slice(m[0].length) };
  }
  return null;
}

// "2x400g tins" / "2 x 400 g tins" -> a single mass-unit line, 800 g total
function takeMultipack(s) {
  const m = s.match(/^(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(g|gram|grams|kg|ml|l)\b\.?\s*(tins?|cans?)?\s*/i);
  if (!m) return null;
  const count = +m[1], each = +m[2];
  const unit = UNIT_LOOKUP[m[3].toLowerCase()] || m[3].toLowerCase();
  return { qty: count * each, qtyLo: count * each, qtyHi: count * each, qtyText: m[0].trim(),
           unit, unitText: m[3], rest: s.slice(m[0].length) };
}

// "1 onion (150g), diced" -> the parenthetical mass overrides the leading count
function massOverride(rest) {
  const m = rest.match(/\((\d+(?:\.\d+)?)\s*(g|gram|grams|kg|ml|l)\)/i);
  if (!m) return null;
  return {
    qty: +m[1], qtyLo: +m[1], qtyHi: +m[1],
    unit: UNIT_LOOKUP[m[2].toLowerCase()] || m[2].toLowerCase(),
    unitText: m[0],
    rest: rest.slice(0, m.index) + rest.slice(m.index + m[0].length),
  };
}

// "juice of 1 lemon" -> qty/unit come from the noun's count, ingredient becomes "lemon juice"
function takeJuiceOf(s) {
  const m = s.match(/^juice of\s+(.+)$/i);
  if (!m) return null;
  const q = takeQty(m[1]) || { qty: 1, qtyLo: 1, qtyHi: 1, qtyText: "", rest: m[1] };
  const noun = q.rest.trim();
  return { qty: q.qty, qtyLo: q.qtyLo, qtyHi: q.qtyHi, qtyText: m[0],
           unit: null, unitText: null, rest: (noun ? noun + " " : "") + "juice" };
}

// ---- prep / state / flags ----------------------------------------------------------------

const PREP_WORDS = new Set([
  "chopped", "diced", "minced", "sliced", "grated", "crushed", "peeled", "melted",
  "softened", "beaten", "sifted", "ground", "zested", "juiced", "shredded", "halved",
  "quartered", "cubed", "crumbled", "trimmed", "rinsed", "drained", "toasted", "roasted",
  "julienned", "mashed", "whisked", "seeded", "pitted", "cored", "finely", "roughly",
  "thinly", "coarsely",
]);
const STATE_WORDS = new Set(["raw", "cooked", "canned", "tinned", "frozen", "dried", "fresh"]);

function splitIngredient(rest) {
  // find first delimiter: comma, "(", " - ", ";"
  let cut = rest.length;
  const dashIx = rest.indexOf(" - ");
  for (const [ix] of [[rest.indexOf(",")], [rest.indexOf("(")], [rest.indexOf(";")], [dashIx]]) {
    if (ix >= 0 && ix < cut) cut = ix;
  }
  let ing = rest.slice(0, cut).trim();
  let tail = rest.slice(cut).trim();

  const flags = { opt: false, taste: false };
  if (/\boptional\b/i.test(rest)) flags.opt = true;
  if (/\bto taste\b/i.test(rest)) flags.taste = true;

  const prep = [];
  let state = null;
  const phrases = tail
    .replace(/[(),;]/g, " ")
    .split(/[-\s]*\bto taste\b[-\s]*/i).join(" ")
    .split(/\boptional\b/i).join(" ")
    .split(",")
    .flatMap((p) => p.split(/\s+and\s+/i))
    .map((p) => p.trim())
    .filter(Boolean);
  for (const phrase of phrases) {
    const words = phrase.split(/\s+/).filter(Boolean);
    for (const w of words) {
      const lw = w.toLowerCase().replace(/[^a-z]/g, "");
      if (STATE_WORDS.has(lw) && !state) state = lw;
      else if (PREP_WORDS.has(lw)) prep.push(lw);
      else if (lw) prep.push(lw); // keep descriptive words too (e.g. "extra virgin")
    }
  }

  return { ing, prep, state, flags };
}

// ---- classify -----------------------------------------------------------------------------

const NOTE_VERBS = /^(preheat|heat|bring|bake|boil|simmer|stir|mix|combine|whisk|fold|add|pour|season|serve|let|remove|place|cover|reduce|rest|cook|blend|drain|garnish|transfer|repeat|meanwhile|set|line|grease|chill|allow|toss)\b/i;

function classify(s) {
  if (!s) return "blank";
  const letters = s.replace(/[^a-zA-Z]/g, "");
  const isAllCaps = letters.length >= 3 && letters === letters.toUpperCase();
  const isHeading = /^(for the|serves?|makes|yields?)\b/i.test(s) || /:$/.test(s) || isAllCaps;
  if (isHeading) return "head";
  const leadsWithQty = new RegExp(`^(${NUM_RE})\\b`).test(s) ||
    new RegExp(`^(${Object.keys(NUM_WORDS).join("|")})\\b`, "i").test(s);
  const wordCount = s.split(/\s+/).filter(Boolean).length;
  if (!leadsWithQty && (NOTE_VERBS.test(s) || wordCount > 12)) return "note";
  return "ing";
}

const ZERO_ING_RE = /^(salt(\s*(and|&)\s*pepper)?|(black\s+)?pepper|water)\.?$/i;

function servingsFromHead(s) {
  const m = s.match(/\b(?:serves?|makes|yields?)\s+(\d+)/i);
  return m ? +m[1] : null;
}

// ---- parseRecipe ----------------------------------------------------------------------------

function parseRecipe(text) {
  const lines = (text || "").split(/\r\n|\r|\n/);
  const rows = [];
  lines.forEach((raw, i) => {
    const norm = normalise(raw);
    const row = {
      i, raw,
      kind: null,
      qty: null, qtyText: null, qtyLo: null, qtyHi: null,
      unit: null, unitText: null,
      ing: null, prep: [],
      state: null,
      flags: { opt: false, taste: false },
      food: null, cands: null, conf: null,
    };

    if (!norm) { row.kind = "blank"; rows.push(row); return; }

    const kind = classify(norm);
    row.kind = kind;

    if (kind === "head") {
      row.ing = norm.replace(/:$/, "").trim();
      const servings = servingsFromHead(norm);
      if (servings) row.servings = servings;
      rows.push(row);
      return;
    }
    if (kind === "note") {
      row.ing = norm;
      rows.push(row);
      return;
    }

    let rest = norm;
    let taken = takeJuiceOf(rest) || takeMultipack(rest) || takeQty(rest);
    if (taken) {
      row.qty = taken.qty; row.qtyLo = taken.qtyLo; row.qtyHi = taken.qtyHi;
      row.qtyText = taken.qtyText;
      rest = taken.rest.replace(/^\s+/, "");
      if (taken.unit !== undefined && taken.unit !== null) {
        row.unit = taken.unit; row.unitText = taken.unitText;
      }
    }

    if (row.unit === null) {
      // indefinite unit words used bare, e.g. "a knob of butter"
      const un = takeUnit(rest);
      if (un) { row.unit = un.unit; row.unitText = un.unitText; rest = un.rest.replace(/^\s+/, ""); }
    }
    rest = rest.replace(/^of\s+/i, "");

    const mo = massOverride(rest);
    if (mo) {
      row.qty = mo.qty; row.qtyLo = mo.qty; row.qtyHi = mo.qty;
      row.unit = mo.unit; row.unitText = mo.unitText;
      rest = mo.rest.replace(/\s{2,}/g, " ").trim();
    }

    const split = splitIngredient(rest);
    row.ing = split.ing;
    row.prep = split.prep;
    row.state = split.state;
    row.flags = split.flags;

    if (ZERO_ING_RE.test(row.ing.trim())) row.kind = "zero";
    rows.push(row);
  });
  return rows;
}

function recipeServings(rows) {
  for (const r of rows) if (r.servings) return r.servings;
  return 1;
}

// ---- exports --------------------------------------------------------------------------

const OD = root.OD || {};
OD.parseRecipe = parseRecipe;
OD.recipeServings = recipeServings;
root.OD = OD;

if (typeof module !== "undefined" && module.exports) module.exports = OD;

})(typeof window !== "undefined" ? window : globalThis);
