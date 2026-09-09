// recipe.js — pasted-recipe parsing and (later) matching/unit conversion.
// A classic script, loaded after support.js in index.html and required directly by node
// under tools/recipe_test.js, so the two never run different code. See RECIPE.md.
"use strict";
(function (root) {

// ---- search: stemming, food objects, ranking ----------------------------------------------
// Moved out of index.html's live search path (was stemWord, the mkFood closure and the
// inline scorer in renderVals) so a Node test and the recipe matcher run the identical code
// the site does. index.html calls OD.stemWord / OD.mkFoods / OD.rankFoods; behaviour is
// unchanged — see the "same top results before/after" check in tools/recipe_test.js.

// Apples is apple. Enough of a stemmer for a shopping list: USDA pluralises the food and
// people type the singular, or the other way round.
function stemWord(w) {
  return w.length > 4 && w.slice(-3) === "ies" ? w.slice(0, -3) + "y"
    : w.length > 4 && (w.slice(-3) === "oes" || w.slice(-3) === "ses" || w.slice(-3) === "xes" || w.slice(-3) === "hes") ? w.slice(0, -2)
      : w.length > 3 && w.slice(-1) === "s" && w.slice(-2) !== "ss" ? w.slice(0, -1)
        : w;
}

// A brand, as USDA writes one: shouted in capitals (QUAKER, MEAD JOHNSON, KFC) or owned by
// somebody (McDonald's, Applebee's). Same rules tools/pool_foods.py uses, so a brand here is
// a brand there.
const BRANDED = /\b(?!NFS\b|NS\b|USDA\b|RTE\b|UPC\b|I{2,3}\b|IV\b)[A-Z]{2,}\b/;
const OWNED = /\b[A-Z][a-z]+'s\b/;

// Turns a parsed library file ({cats, foods, pools}) into the food objects the search and
// the recipe matcher both read: name/category/macros off the array, plus the derived fields
// (nl/w/ns/h1/br) every match against a food needs.
function mkFoods(d) {
  const mkFood = a => {
    const fo = { name: a[0], cat: d.cats[a[1]], kcal: a[2], p: a[3], c: a[4], fb: a[5], f: a[6], sf: a[7], sg: a[8] };
    if (a[9]) fo.mu = "ml";
    // Eleventh element: this is the entry someone typing the plain word meant.
    if (a[10]) fo.cm = 1;
    // Split once here rather than on every keystroke: search works word by word.
    fo.nl = fo.name.toLowerCase();
    fo.w = fo.nl.split(/[^a-z0-9]+/).filter(Boolean);
    // The singular of every word, joined — so "berry" can reach "blueberries".
    fo.ns = fo.w.map(stemWord).join(" ");
    // And the head of the name on its own: "Apples, raw, with skin" is an apple,
    // "Apple juice, canned or bottled" is a juice.
    fo.h1 = fo.nl.split(",")[0].split(/[^a-z0-9]+/).filter(Boolean).map(stemWord).join(" ");
    fo.br = BRANDED.test(fo.name) || OWNED.test(fo.name) ? 1 : 0;
    // Twelfth and thirteenth: what one household serving of this food weighs, and
    // what to call it — "182 g", "MEDIUM".
    if (a[11]) { fo.pg = a[11]; fo.pn = a[12]; }
    // Fourteenth on: what the rest of 100 g is. Carbohydrate is reported by
    // difference, so water + protein + carb + fat + ash + alcohol is 100 g by
    // construction, and the food can be drawn as well as listed. Then the two fats
    // that break the fat figure down. tools/add_composition.py writes them.
    if (a.length > 13) {
      fo.wa = a[13]; fo.ah = a[14]; fo.mo = a[15]; fo.po = a[16]; fo.al = a[17];
      fo.tr = a[18] || 0;
    }
    return fo;
  };
  const foods = d.foods.map(mkFood);
  // The pools: one typical row per family of near-identical entries, the mean of its
  // members, written by tools/pool_foods.py. Twentieth element is the members, twenty-first
  // the words every member shares that the name leaves out — folded into what the search
  // reads so the word still finds the pool.
  (d.pools || []).forEach(a => {
    const fo = mkFood(a);
    fo.pool = (a[19] || []).map(i => d.foods[i][0]);
    // Everything from the first "·" is the mark, not a word of the food.
    const plain = fo.name.split(" · ")[0].toLowerCase();
    fo.nl = plain;
    fo.w = plain.split(/[^a-z0-9]+/).filter(Boolean);
    fo.ns = fo.w.map(stemWord).join(" ");
    fo.h1 = plain.split(",")[0].split(/[^a-z0-9]+/).filter(Boolean).map(stemWord).join(" ");
    const alias = a[20] || [];
    if (alias.length) {
      fo.nl += " " + alias.join(" ");
      fo.w = fo.w.concat(alias);
      fo.ns = fo.w.map(stemWord).join(" ");
    }
    // Each member is told which pool stands for it.
    (a[19] || []).forEach(i => { if (foods[i]) foods[i].ofPool = fo; });
    foods.push(fo);
  });
  return foods;
}

// Filters `list` to the foods a query q matches and scores each with fo._hit, the same
// scoring renderVals used to sort by. Returns list unchanged for an empty query — the
// caller (index.html) still sorts, applies the category filter and pool scoping.
function rankFoods(list, q) {
  const qWords = q ? q.split(/\s+/).filter(Boolean) : [];
  if (!qWords.length) return list;
  const qStems = qWords.map(stemWord);
  // What the food is called, before USDA starts qualifying it.
  const qHead = qStems.join(" ");
  const qJoin = qWords.join(" ");
  // How the query landed decides the order, and nothing else can overturn it: a whole word
  // (plural or not), then the start of a longer word, then a hit buried inside one.
  const WHOLE_PTS = 20, START_PTS = 12, INSIDE_PTS = 4;
  // The rest settle foods that landed the same way: being the everyday one, opening the
  // name, landing in its first words, and how much of the word the query spelled, and the
  // whole head of the name matched with nothing else.
  const COMMON_PTS = 7, LEAD_PTS = 1, PART_LEAD_PTS = 9, NEAR_PTS = 3, CLOSE_PTS = 3, HEAD_PTS = 10;
  // Not being a brand is worth a whole tier.
  const PLAIN_PTS = 8;
  // A pool matches only through words every member has, so whenever it matches at all, so
  // does each of its members; enough to clear the everyday bonus, since the pool is the
  // everyday answer.
  const POOL_PTS = 9;
  return list.filter(fo => {
    const n = fo.nl, words = fo.w;
    let hit = 0, near = 99, spare = 99, firstTier = 0;
    for (let i = 0; i < qWords.length; i++) {
      const tok = qWords[i], tokStem = qStems[i];
      if (n.indexOf(tok) < 0 && fo.ns.indexOf(tokStem) < 0) return false;
      let best = 0, bestAt = 99, bestSpare = 99;
      for (let j = 0; j < words.length; j++) {
        const wd = words[j];
        // Only a plural reads differently from its stem, so only plurals pay for one.
        const wdStem = wd.charCodeAt(wd.length - 1) === 115 ? stemWord(wd) : wd;
        let at = wd.indexOf(tok);
        if (at < 0) at = wdStem.indexOf(tokStem);
        if (at < 0) continue;
        // Filling a whole word only counts for the top tier if there was a word's worth of
        // it: "t" fills the "t" of "t-bone steak" exactly, and means nothing by doing so.
        const pts = wdStem === tokStem ? (tokStem.length > 2 ? WHOLE_PTS : START_PTS)
          : at === 0 ? START_PTS : INSIDE_PTS;
        const left = wdStem.length - tokStem.length;
        if (pts > best || (pts === best && j < bestAt)) { best = pts; bestAt = j; bestSpare = left; }
        if (best === WHOLE_PTS && bestAt === 0) break;
      }
      // A token that straddles a break ("3.25") still counts, just weakly.
      hit += best || INSIDE_PTS;
      if (i === 0) firstTier = best || INSIDE_PTS;
      if (bestAt < near) near = bestAt;
      if (bestSpare < spare) spare = bestSpare;
    }
    if (fo.cm) hit += COMMON_PTS;
    if (!fo.br) hit += PLAIN_PTS;
    if (fo.pool) hit += POOL_PTS;
    // "chicken br" opening the name is the user typing the name itself, and it outranks
    // being the everyday one. Guarded so a single whole word keeps its old, quiet +1.
    if (n.indexOf(qJoin) === 0 && (qWords.length > 1 || firstTier !== WHOLE_PTS)) hit += PART_LEAD_PTS;
    else if (n.indexOf(qWords[0]) === 0) hit += firstTier === WHOLE_PTS ? LEAD_PTS : PART_LEAD_PTS;
    hit += Math.max(0, NEAR_PTS - near);
    hit += Math.max(0, CLOSE_PTS - spare);
    // The whole of the name's head, and nothing else: an apple rather than an apple juice.
    if (fo.h1 === qHead) hit += HEAD_PTS;
    // Scratch field, rewritten on every keystroke; only the sort after this reads it.
    fo._hit = hit;
    return true;
  });
}

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
  // range: "1-2" / "1 to 2". Note: no \b after the second number — "1-2tbsp" (no space
  // before the unit) is as common in pasted recipes as "400g" is, and a digit run followed
  // directly by a letter is never a false split since NUM_RE already consumes every digit.
  let m = s.match(new RegExp(`^(${NUM_RE})\\s*(?:-|to)\\s*(${NUM_RE})\\s*`, "i"));
  if (m) {
    const lo = numVal(m[1]), hi = numVal(m[2]);
    return { qty: (lo + hi) / 2, qtyLo: lo, qtyHi: hi, qtyText: m[0].trim(), rest: s.slice(m[0].length) };
  }
  // plain number, possibly mixed fraction — same reasoning, no \b before the unit letters.
  m = s.match(new RegExp(`^(${NUM_RE})\\s*`));
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
  const m = s.match(/^((\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(g|gram|grams|kg|ml|l))\b\.?\s*(tins?|cans?)?\s*/i);
  if (!m) return null;
  const count = +m[2], each = +m[3];
  const unit = UNIT_LOOKUP[m[4].toLowerCase()] || m[4].toLowerCase();
  return { qty: count * each, qtyLo: count * each, qtyHi: count * each, qtyText: m[1].trim(),
           unit, unitText: m[4], rest: s.slice(m[0].length) };
}

// The spellings of the units a bracketed size can be given in — mass and liquid measure,
// longest first so "fl oz" is read before "oz".
const SIZE_UNIT_RE = ["g", "kg", "oz", "lb", "ml", "l", "floz"]
  .flatMap((k) => UNIT_TABLE[k])
  .sort((a, b) => b.length - a.length)
  .map((sp) => sp.replace(/\s+/, "\\s+"))
  .join("|");
const PACK_WORDS = "cans?|tins?|packages?|pkgs?|packets?|jars?|bottles?|bags?|boxe?s?|cartons?|containers?|pouch(?:es)?|tubs?";

// "1 (10.5 ounce) can condensed soup", "2 (14 oz) cans tomatoes": a size in brackets straight
// after the count is the size of each container, so the line is count × size of the food in
// that unit, and the container word that follows names the measure rather than the food.
// Without this the bracket was read as the start of the notes and the ingredient was empty.
function takePackSize(s) {
  const m = s.match(new RegExp("^\\((" + NUM_RE + ")\\s*(" + SIZE_UNIT_RE + ")\\.?\\)\\s*(?:(" + PACK_WORDS + ")\\b\\.?\\s*)?(?:of\\s+)?", "i"));
  if (!m) return null;
  const unit = UNIT_LOOKUP[m[2].toLowerCase().replace(/\s+/, " ")];
  if (!unit) return null;
  return { size: numVal(m[1]), unit,
           unitText: m[1] + " " + unit + (m[3] ? " " + m[3].toLowerCase() : ""),
           rest: s.slice(m[0].length) };
}

// "1 onion (150g), diced", "2 onions (300 g)": a size in brackets after the food is the whole
// amount, and overrides the leading count.
function massOverride(rest) {
  const m = rest.match(new RegExp("\\((\\d+(?:\\.\\d+)?)\\s*(" + SIZE_UNIT_RE + ")\\.?\\)", "i"));
  if (!m) return null;
  const unit = UNIT_LOOKUP[m[2].toLowerCase().replace(/\s+/, " ")];
  if (!unit) return null;
  return {
    qty: +m[1], qtyLo: +m[1], qtyHi: +m[1],
    unit, unitText: m[0],
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

const NOTE_VERBS = /^(preheat|heat|bring|bake|boil|simmer|stir|mix|combine|whisk|fold|add|pour|season|serve|let|remove|place|cover|reduce|rest|cook|blend|drain|garnish|transfer|repeat|meanwhile|set|line|grease|chill|allow|toss|divide|cream|sprinkle|spread|top|taste|adjust|discard|layer|arrange|increase|decrease|continue|return|sift|turn|flip|press|knead|roll|shape|dust|brush|squeeze|crack|separate|whip|enjoy|refrigerate|leave|use|check|slice|cut|arrange)\b/i;

function leadsWithQty(s) {
  return new RegExp(`^(${NUM_RE})\\b`).test(s) ||
    new RegExp(`^(${Object.keys(NUM_WORDS).join("|")})\\b`, "i").test(s);
}

function classify(s) {
  if (!s) return "blank";
  const letters = s.replace(/[^a-zA-Z]/g, "");
  const isAllCaps = letters.length >= 3 && letters === letters.toUpperCase();
  const isHeading = /^(for the|serves?|makes|yields?)\b/i.test(s) || /:$/.test(s) || isAllCaps;
  if (isHeading) return "head";
  const leads = leadsWithQty(s);
  const wordCount = s.split(/\s+/).filter(Boolean).length;
  // A method step reads as a sentence — it ends with a full stop or exclamation mark, which
  // an ingredient line essentially never does — or opens with an imperative verb, or simply
  // runs long. None of that applies to a line that leads with a quantity.
  if (!leads && (NOTE_VERBS.test(s) || wordCount > 12 || /[.!]$/.test(s))) return "note";
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
  // A single pasted line is someone testing an ingredient, not a titled recipe — the title
  // override below only makes sense once there is a body for the title to sit in front of.
  const hasBody = lines.filter((l) => normalise(l)).length > 1;
  const rows = [];
  let seenContent = false;
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

    // The first non-blank line of a pasted recipe is its title more often than its first
    // ingredient — "Chicken curry" is neither ALL CAPS nor "For the ..." nor a sentence, so
    // classify() alone would call it an ingredient. Only overridden when it doesn't itself
    // lead with a quantity, so a recipe pasted without a title still starts on its own row.
    let kind = classify(norm);
    if (hasBody && !seenContent && kind === "ing" && !leadsWithQty(norm)) kind = "head";
    seenContent = true;
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

    if (row.unit === null && taken && taken.unit == null) {
      const ps = takePackSize(rest);
      if (ps) {
        row.qty = row.qty * ps.size; row.qtyLo = row.qty; row.qtyHi = row.qty;
        row.unit = ps.unit; row.unitText = ps.unitText;
        rest = ps.rest.replace(/^\s+/, "");
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

// ---- matcher (Phase 2) ------------------------------------------------------------------
// matchLine(line, foods, aliases) turns a parsed row's ingredient text into the food a
// recipe means, re-weighting rankFoods' word-match score for what a recipe wants that a
// plate search does not: raw over frozen, plain over branded, the alias's world knowledge
// ("caster sugar" is sugar) over a string match that cannot have it.

const ING_STOPWORDS = new Set(["fresh", "of", "good", "quality", "organic"]);

// A recipe means the raw form unless it says otherwise, so anything that reads as prepared
// costs a candidate unless the line (or the alias that found it) names that state.
const PROCESS_WORDS = [
  "frozen", "dehydrated", "dried", "canned", "cooked", "boiled", "baked", "fried",
  "roasted", "juice", "babyfood", "restaurant", "fast foods", "shake", "mix", "powder",
  "with salt", "smoked", "pickled", "sweetened", "instant",
];

function stemJoin(text) {
  return (text || "").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean).map(stemWord).join(" ");
}

// The alias whose phrase is the longest match against the ingredient text, stemmed both
// sides so "caster sugars" still finds "caster sugar".
function findAlias(ing, aliases) {
  const ingStemmed = stemJoin(ing);
  let best = null, bestLen = 0;
  for (const alias of aliases || []) {
    for (const phrase of alias.m || []) {
      const phraseStemmed = stemJoin(phrase);
      if (!phraseStemmed) continue;
      const hit = ingStemmed === phraseStemmed
        || ingStemmed.indexOf(" " + phraseStemmed + " ") >= 0
        || ingStemmed.indexOf(phraseStemmed + " ") === 0
        || ingStemmed.slice(-phraseStemmed.length - 1) === " " + phraseStemmed;
      if (hit && phraseStemmed.length > bestLen) { best = alias; bestLen = phraseStemmed.length; }
    }
  }
  return best;
}

function isPlain(fo) {
  return !PROCESS_WORDS.some((w) => fo.nl.indexOf(w) >= 0);
}

// The recipe re-weighting rankFoods never does itself: raw/plain preferred, process words
// penalised unless the line's own state calls for them, an alias pin placed first.
function reweight(fo, pinName, lineState, aliasState) {
  let score = fo._hit || 0;
  if (isPlain(fo)) score += 8;
  for (const w of PROCESS_WORDS) {
    if (fo.nl.indexOf(w) < 0) continue;
    const named = (lineState && w.indexOf(lineState) >= 0) || (aliasState && w.indexOf(aliasState) >= 0);
    score += named ? 6 : -10;
  }
  if (pinName && fo.name === pinName) score += 40;
  score -= 0.2 * fo.name.length;
  return score;
}

function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

// rankFoods expects a plain lowercase, punctuation-free query, same as the search box hands
// it — a pin name like "Sugars, granulated" has to be cleaned to "sugars granulated" first.
function cleanQuery(text) {
  return (text || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}

const RCP_CANDS = 8;

// matchLine(line, foods, aliases) -> {food, cands, conf, review}. `line` is a row from
// parseRecipe (reads .ing/.state); `foods` is OD.mkFoods(json) output.
function matchLine(line, foods, aliases) {
  const ing = (line && line.ing) || "";
  const alias = findAlias(ing, aliases);
  const aliasHit = !!alias;
  const query = cleanQuery(alias ? (alias.q || alias.pin || ing) : Array.from(
    new Set(stemJoin(ing).split(" ").filter((w) => w && !ING_STOPWORDS.has(w)))
  ).join(" ") || ing);
  // Whole-word only: "salted" must not fire off the "unsalted" in "unsalted butter".
  const ingWords = new Set(ing.toLowerCase().split(/[^a-z0-9%]+/).filter(Boolean));
  const prepWords = new Set((line.prep || []).flatMap((p) => p.split(/[^a-z0-9%]+/).filter(Boolean)));
  const keepWords = (alias && alias.keep || []).filter((w) => ingWords.has(w) || prepWords.has(w));
  const fullQuery = keepWords.length ? query + " " + keepWords.join(" ") : query;

  let weak = false;
  let cands = rankFoods(foods.slice(), fullQuery);
  if (!cands.length && keepWords.length) cands = rankFoods(foods.slice(), query);
  if (!cands.length) {
    weak = true;
    const head = stemJoin(ing).split(" ")[0] || "";
    cands = rankFoods(foods.slice(), head);
  }

  const pinName = alias && alias.pin;
  const lineState = line && line.state;
  const aliasState = alias && alias.state;
  cands.forEach((fo) => { fo._rcp = reweight(fo, pinName, lineState, aliasState); });
  cands.sort((a, b) => b._rcp - a._rcp);
  cands = cands.slice(0, RCP_CANDS);

  const top = cands[0] || null;
  const h1 = top ? top._rcp : 0;
  const h2 = cands[1] ? cands[1]._rcp : 0;
  const conf = h1 > 0 ? clamp01((h1 - h2) / h1) * (aliasHit ? 1 : 0.7) : 0;
  const review = !top || (!aliasHit && conf < 0.25) || weak || !!(top && top.br);

  return {
    food: top ? top.name : null,
    cands: cands.map((fo) => fo.name),
    conf,
    review,
    weak,
  };
}

// ---- units (Phase 3) --------------------------------------------------------------------
// gramsFor(line, fo, units) -> {g, how, label}. `units` is data/units.json, parsed.
// Resolution order (first hit wins, `how` records it): mass unit; volume, preferring the
// food's own per-portion weight (fo.pg/fo.pn) over a generic density table; count, same
// preference; a bare quantity with no unit read as "each"; otherwise a default that keeps a
// review-worthy row from vanishing (0 g for "to taste", 100 g otherwise).

const RCP_MAX = 5000;

function countWordKey(ing, table) {
  const stemmed = stemJoin(ing);
  let best = null, bestLen = 0;
  for (const key in table || {}) {
    const keyStemmed = stemJoin(key);
    if (keyStemmed && stemmed.indexOf(keyStemmed) >= 0 && keyStemmed.length > bestLen) {
      best = key; bestLen = keyStemmed.length;
    }
  }
  return best;
}

function densityFor(fo, units) {
  const words = (units.density && units.density.word) || [];
  for (const [word, d] of words) if (fo.nl.indexOf(word) >= 0) return d;
  const cat = units.density && units.density.cat && units.density.cat[fo.cat];
  return cat != null ? cat : 1.0;
}

function countGrams(unit, ing, fo, units) {
  const labelUnits = fo.pn && units.labels && units.labels[fo.pn];
  if (labelUnits && labelUnits.indexOf(unit) >= 0 && fo.pg) return fo.pg;
  const word = countWordKey(ing, units.count && units.count.word);
  if (word && units.count.word[word][unit] != null) return units.count.word[word][unit];
  if (units.count && units.count.default && units.count.default[unit] != null) return units.count.default[unit];
  return null;
}

function labelText(line) {
  const parts = [line.qtyText, line.unitText].filter(Boolean);
  return parts.length ? parts.join(" ") : (line.qty != null ? String(line.qty) : "");
}

function gramsFor(line, fo, units) {
  const label = labelText(line);
  if (!fo) return { g: 0, how: "none", label };

  const qty = line.qty != null ? line.qty : 1;
  const unit = line.unit;

  if (unit && units.mass && units.mass[unit] != null) {
    return { g: Math.min(RCP_MAX, qty * units.mass[unit]), how: "mass", label };
  }

  if (unit && units.volume && units.volume[unit] != null) {
    const labelUnits = fo.pn && units.labels && units.labels[fo.pn];
    const anchor = labelUnits && labelUnits.find((u) => units.volume[u] != null);
    if (anchor && fo.pg) {
      const g = qty * fo.pg * (units.volume[unit] / units.volume[anchor]);
      return { g: Math.min(RCP_MAX, g), how: "pg", label };
    }
    const density = densityFor(fo, units);
    return { g: Math.min(RCP_MAX, qty * units.volume[unit] * density), how: "density", label };
  }

  if (unit) {
    const g = countGrams(unit, line.ing || "", fo, units);
    if (g != null) return { g: Math.min(RCP_MAX, qty * g), how: "count", label };
  }

  if (!unit && line.qty != null) {
    const g = countGrams("each", line.ing || "", fo, units);
    if (g != null) return { g: Math.min(RCP_MAX, qty * g), how: "count", label };
  }

  return { g: line.flags && line.flags.taste ? 0 : 100, how: "none", label, review: true };
}

// ---- exports --------------------------------------------------------------------------

const OD = root.OD || {};
OD.stemWord = stemWord;
OD.mkFoods = mkFoods;
OD.rankFoods = rankFoods;
OD.parseRecipe = parseRecipe;
OD.recipeServings = recipeServings;
OD.matchLine = matchLine;
OD.gramsFor = gramsFor;
root.OD = OD;

if (typeof module !== "undefined" && module.exports) module.exports = OD;

})(typeof window !== "undefined" ? window : globalThis);
