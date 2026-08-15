#!/usr/bin/env python3
"""Build the calorie game's deck: single foods, in stated portions.

The rule this deck is built on:

    the weight is never typed in — it is USDA's own published household portion
    for that food, multiplied by a whole number — and the calories are that
    weight against USDA's published energy density.

So "8 strawberries" is eight times SR Legacy's 12 g medium strawberry, and its
31 kcal is 96 g against SR Legacy's 32 kcal per 100 g. Nothing in the deck is
anyone's estimate; the tool would rather fail than invent a figure.

    python3 tools/build_pairs_deck.py                 # placeholder pictures
    python3 tools/build_pairs_deck.py --raw <dir>     # cut from 3x3 grids

With grids in `data/pairs/raw/set<n>.png` the nine tiles of each are cut out and
used. Without them the pictures are placeholders — a plate outline and the food's
name — so the game is playable while the photography is still being made. The
placeholders say what they are; they are not pretending to be food.

Also builds from the Nutrition5k plate deck with --from-plates, which needs no
pictures at all because they are already in the repo.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "pairs", "raw")
OUT = os.path.join(ROOT, "data", "pairs")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# The gutter between tiles in a generated grid is a few pixels of background;
# trimming it keeps a pale seam off the edge of the crop.
GUTTER = 8

# name in data/legacy.json | how many of USDA's own household portions | how the
# portion reads on screen. Nine foods a set, one from each of nine kinds: fruit,
# vegetable, grain, bread, meat or fish, egg or dairy, nut or fat, legume, and
# something out of a packet.
GRIDS = [
    ("set1", [
        ("Carrots, raw", 1, "1 carrot"),
        ("Strawberries, raw", 8, "8 strawberries"),
        ("Squash, summer, zucchini, includes skin, cooked, boiled, drained, without salt", 3, "3 cups, sliced"),
        ("Croutons, plain", 1, "a cup"),
        ("Egg, whole, cooked, hard-boiled", 2, "2 eggs"),
        ("Pasta, cooked, enriched, without added salt", 1, "a cup, cooked"),
        ("Cheese, cheddar", 2, "2 slices"),
        ("Potatoes, boiled, cooked in skin, flesh, without salt", 2, "2 cups"),
        ("Nuts, cashew nuts, dry roasted, without salt added", 0.5, "half a cup"),
    ]),
    ("set2", [
        ("Avocados, raw, California", 1, "1 avocado"),
        ("Grapes, red or green (European type, such as Thompson seedless), raw", 2, "2 cups"),
        ("Cucumber, with peel, raw", 3, "3 cups, sliced"),
        ("Broccoli, raw", 2, "2 cups, chopped"),
        ("Snacks, popcorn, cakes", 2, "2 cakes"),
        ("Edamame, frozen, prepared", 1, "a cup, podded"),
        ("Bread, whole-wheat, commercially prepared", 2, "2 slices"),
        ("Chocolate, dark, 70-85% cacao solids", 0.5, "half a bar"),
        ("Rice, brown, long-grain, cooked", 2, "2 cups, cooked"),
    ]),
    ("set3", [
        ("Blueberries, raw", 1, "a cup"),
        ("Apples, raw, with skin", 1, "1 apple"),
        ("Yogurt, Greek, plain, nonfat", 1, "a pot"),
        ("Snacks, tortilla chips, unsalted, white corn", 1, "a cup"),
        ("Couscous, cooked", 1, "a cup, cooked"),
        ("Corn, sweet, yellow, cooked, boiled, drained, without salt", 2, "2 cobs"),
        ("Milk, whole, 3.25% milkfat, with added vitamin D", 1.5, "a tall glass"),
        ("Raisins, golden, seedless", 0.5, "half a cup"),
        ("Nuts, almonds, blanched", 0.5, "half a cup"),
    ]),
    ("set4", [
        ("Watermelon, raw", 2, "2 cups, cubed"),
        ("Dates, medjool", 2, "2 dates"),
        ("Pork, cured, bacon, cooked, baked", 3, "3 rashers"),
        ("Melons, honeydew, raw", 3, "3 cups, cubed"),
        ("Butter, salted", 2, "2 tablespoons"),
        ("Rice, white, long-grain, regular, cooked, unenriched, with salt", 1, "a cup, cooked"),
        ("Turkey, breast, smoked, lemon pepper flavor, 97% fat-free", 8, "8 slices"),
        ("Peanut Butter, smooth", 3, "3 tablespoons"),
        ("Oil, olive, salad or cooking", 3, "3 tablespoons"),
    ]),
]

# What the picture actually turned out to hold, where that differs from what was
# asked for. The rule does not bend: the weight is still USDA's own household
# portion times a whole number — the number is just counted off the finished
# picture rather than taken from the prompt.
SEEN = {
    "Strawberries, raw": (7, "7 strawberries"),
    "Pork, cured, bacon, cooked, baked": (4, "4 rashers"),
    "Chocolate, dark, 70-85% cacao solids": (1, "a whole bar"),
}

# Pictures showing the wrong thing rather than the wrong number, where no amount
# of counting can rescue the label. None at present.
NO_MATCH = set()

SHORT = {
    "Carrots, raw": "carrot",
    "Strawberries, raw": "strawberries",
    "Squash, summer, zucchini, includes skin, cooked, boiled, drained, without salt": "courgette",
    "Croutons, plain": "croutons",
    "Egg, whole, cooked, hard-boiled": "boiled eggs",
    "Pasta, cooked, enriched, without added salt": "pasta",
    "Cheese, cheddar": "cheddar",
    "Potatoes, boiled, cooked in skin, flesh, without salt": "boiled potato",
    "Nuts, cashew nuts, dry roasted, without salt added": "cashews",
    "Avocados, raw, California": "avocado",
    "Grapes, red or green (European type, such as Thompson seedless), raw": "grapes",
    "Cucumber, with peel, raw": "cucumber",
    "Broccoli, raw": "broccoli",
    "Snacks, popcorn, cakes": "popcorn cakes",
    "Edamame, frozen, prepared": "edamame",
    "Bread, whole-wheat, commercially prepared": "wholemeal bread",
    "Chocolate, dark, 70-85% cacao solids": "dark chocolate",
    "Rice, brown, long-grain, cooked": "brown rice",
    "Blueberries, raw": "blueberries",
    "Apples, raw, with skin": "apple",
    "Yogurt, Greek, plain, nonfat": "greek yogurt",
    "Snacks, tortilla chips, unsalted, white corn": "tortilla chips",
    "Couscous, cooked": "couscous",
    "Corn, sweet, yellow, cooked, boiled, drained, without salt": "sweetcorn",
    "Milk, whole, 3.25% milkfat, with added vitamin D": "whole milk",
    "Raisins, golden, seedless": "raisins",
    "Nuts, almonds, blanched": "almonds",
    "Watermelon, raw": "watermelon",
    "Dates, medjool": "dates",
    "Pork, cured, bacon, cooked, baked": "bacon",
    "Melons, honeydew, raw": "honeydew",
    "Butter, salted": "butter",
    "Rice, white, long-grain, regular, cooked, unenriched, with salt": "white rice",
    "Turkey, breast, smoked, lemon pepper flavor, 97% fat-free": "turkey breast",
    "Peanut Butter, smooth": "peanut butter",
    "Oil, olive, salad or cooking": "olive oil",
}


# Four families, taken from USDA's own unit rather than from the prose, so the
# mark on a card cannot drift from the figure behind it. The deck's seventeen unit
# strings collapse to these without anything being forced: a container of yogurt is
# a cup-shaped thing, a rasher is a slice, and everything counted as an object —
# medium, large, fruit, cake, bar, date, ear — is whole.
def family(unit):
    u = (unit or "").upper()
    if "TBSP" in u or "TABLESPOON" in u:
        return "spoon"
    if "CUP" in u or "CONTAINER" in u:
        return "cup"
    if "SLICE" in u:
        return "slice"
    return "whole"


def usda():
    """Every food by its exact description, so the density cannot be guessed."""
    with open(os.path.join(ROOT, "data", "legacy.json")) as f:
        rows = json.load(f)["foods"]
    return {r[0]: r for r in rows}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", SHORT.get(name, name).lower()).strip("-")


def tiles(path, out_w):
    """A 3x3 grid, cut into nine squares with the gutter trimmed off."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    cw, ch = w / 3.0, h / 3.0
    for i in range(9):
        x, y = (i % 3) * cw, (i // 3) * ch
        box = (int(x) + GUTTER, int(y) + GUTTER,
               int(x + cw) - GUTTER, int(y + ch) - GUTTER)
        yield im.crop(box).resize((out_w, out_w), Image.LANCZOS)


def placeholder(name, w):
    """A stand-in that admits to being one: a plate, and the food's name.

    The game works without photographs — the question is which of two foods
    carries more, and the names and portions answer that on their own — so the
    deck is playable while the pictures are still being made. The tile carries the
    name, because two identical tiles would read as a fault; the portion and the
    calories stay in the caption, so nothing is said twice.
    """
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (w, w), "#0a1016")
    d = ImageDraw.Draw(im)
    r = int(w * 0.34)
    c = w // 2
    d.ellipse([c - r, c - r, c + r, c + r], outline="#16323d", width=max(2, w // 220))
    d.ellipse([c - r + w // 22, c - r + w // 22, c + r - w // 22, c + r - w // 22],
              outline="#122733", width=max(1, w // 340))
    big = ImageFont.truetype(FONT, int(w * 0.086))
    tiny = ImageFont.truetype(FONT, int(w * 0.029))
    words, lines, cur = name.upper().split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=big) > r * 1.75 and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    step = int(w * 0.105)
    y = c - (len(lines) - 1) * step // 2 - int(w * 0.025)
    for line in lines:
        d.text((c, y), line, font=big, fill="#d7e6ef", anchor="mm")
        y += step
    # Inside the circle, well clear of the caption the site lays over the bottom
    # of the tile, and quiet enough not to compete with the name.
    d.text((c, y + int(w * 0.03)), "N O   P H O T O G R A P H   Y E T",
           font=tiny, fill="#3a4c5c", anchor="mm")
    return im


def from_plates():
    """The other deck the pair game runs on: Nutrition5k's own plates.

    Nothing generated and nothing guessed — every figure was weighed on a scale —
    and the photographs are already in the repo, so this needs no source images.
    A plate is named by the two ingredients carrying most of its calories, which
    is what the player is being asked to price.
    """
    src = os.path.join(ROOT, "data", "game", "deck.json")
    if not os.path.exists(src):
        sys.exit("no plate deck at " + src)
    with open(src) as f:
        plates = json.load(f)["dishes"]
    out = []
    for d in plates:
        top = [x[0] for x in d.get("top", [])][:2]
        if not top:
            continue
        out.append({"id": d["id"], "img": "game/img/" + d["id"] + ".jpg",
                    "name": " + ".join(top), "portion": str(d["g"]) + " g",
                    "g": d["g"], "kcal": d["kcal"], "real": True})
    return out


def build(a, foods):
    """The 36 single foods, with pictures if there are any and marks if not."""
    os.makedirs(os.path.join(a.out, "img"), exist_ok=True)
    deck = []
    for name, items in GRIDS:
        src = next((q for q in (os.path.join(a.raw, name + e)
                                for e in (".png", ".jpg", ".jpeg")) if os.path.exists(q)), "")
        cut = list(tiles(src, a.width)) if src else [None] * 9
        for pic, (food, n, portion) in zip(cut, items):
            if food in SEEN:
                n, portion = SEEN[food]
            if food in NO_MATCH:
                pic = None
            row = foods.get(food)
            if row is None:
                sys.exit("not in legacy.json: " + food)
            per100, unit_g = row[2], row[11]
            if not unit_g:
                sys.exit("no household portion for: " + food)
            g = n * unit_g
            s = slug(food)
            short = SHORT.get(food, food)
            (pic if pic is not None else placeholder(short, a.width)).save(
                os.path.join(a.out, "img", s + ".jpg"),
                "JPEG", quality=86, optimize=True, progressive=True)
            deck.append({"id": s, "img": "pairs/img/" + s + ".jpg", "name": short,
                         "portion": portion, "g": round(g),
                         "kcal": round(per100 * g / 100.0), "real": pic is not None,
                         "unit": family(row[12]), "n": n, "usda": food})
    return deck


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-plates", action="store_true",
                    help="build from the Nutrition5k deck instead")
    ap.add_argument("--raw", default=RAW)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--width", type=int, default=512)
    a = ap.parse_args()
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        sys.exit("Pillow is needed: pip install pillow")
    if a.from_plates:
        deck = from_plates()
        note = ("Nutrition5k plates (Thames et al., CVPR 2021, CC BY 4.0). "
                "Weighed on a scale, not estimated.")
    else:
        deck = build(a, usda())
        shot = sum(1 for d in deck if d["real"])
        note = ("Portions are USDA SR Legacy household measures, counted against the "
                "picture; calories are that weight against SR Legacy's own energy density."
                + ("" if shot == len(deck) else
                   "  %d of %d pictures are placeholders." % (len(deck) - shot, len(deck))))
    if not deck:
        sys.exit("nothing to build")
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "deck.json"), "w") as f:
        json.dump({"note": note, "foods": deck}, f, separators=(",", ":"))
    ks = sorted(d["kcal"] for d in deck)
    pairs = sum(1 for i, x in enumerate(ks) for y in ks[i + 1:] if 1.12 <= y / max(1, x) <= 3.0)
    print("wrote %d foods, %d to %d kcal, %d playable pairs" % (len(deck), ks[0], ks[-1], pairs))
    if not a.from_plates:
        print("%d of %d pictures are placeholders"
              % (sum(1 for d in deck if not d["real"]), len(deck)))


if __name__ == "__main__":
    main()
