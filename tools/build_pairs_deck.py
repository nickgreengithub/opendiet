#!/usr/bin/env python3
"""Build the calorie game's second deck: single foods, in stated portions.

The photographed deck is Nutrition5k — real cafeteria plates, weighed on a
scale. This one is the opposite trade: the pictures are generated, so they are
clean and consistent and show one food at a time, but nothing about them was
measured. That has to be handled rather than glossed over, so the rule here is:

    the guess is only ever the weight; the calories per 100 g are always USDA.

Every entry names a food in `data/legacy.json` and a portion in grams. Where the
generated image matched what was asked for, the grams are USDA's own household
portion times a whole number and `sure` is true. Where it did not — nine
strawberries instead of eight, one slice of bread instead of two — the grams are
read off the picture instead, and `sure` is false. Either way the energy density
is the published figure for that food, never an invention.

    python3 tools/build_pairs_deck.py

Reads data/pairs/raw/set<n>.png — a 3x3 grid of nine tiles — and writes
data/pairs/img/<slug>.jpg plus data/pairs/deck.json.
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

# The gutter between tiles is a few pixels of background; trimming it keeps a
# pale seam off the edge of the crop, where it would read as part of the cloth.
GUTTER = 8

# name in data/legacy.json | grams | how the portion reads | did the picture
# match what was asked for. The name has to be the exact USDA description, since
# that is what carries the energy density.
GRIDS = [
    ("set1", [
        ("Strawberries, raw", 108, "9 strawberries", False),
        ("Carrots, raw", 183, "3 carrots", True),
        ("Rice, white, long-grain, regular, cooked, enriched, with salt", 158, "a cup, cooked", True),
        ("Bread, whole-wheat, commercially prepared", 64, "2 slices", True),
        ("Chicken, broilers or fryers, breast, meat only, cooked, fried", 150, "a breast, cooked", False),
        ("Egg, whole, cooked, hard-boiled", 50, "1 egg, halved", False),
        ("Nuts, almonds", 27, "22 almonds", False),
        ("Lentils, raw", 150, "a bowl, dry", False),
        ("Candies, milk chocolate", 25, "4 squares", False),
    ]),
    ("set2", [
        ("Bananas, raw", 118, "1 banana", True),
        ("Broccoli, raw", 91, "a cup, chopped", True),
        ("Rice, brown, long-grain, cooked", 202, "a cup, cooked", True),
        ("Bagels, wheat", 98, "1 bagel", True),
        ("Pork, cured, bacon, cooked, baked", 32, "4 rashers", True),
        ("Cheese, cheddar", 56, "2 slices", True),
        ("Oil, olive, salad or cooking", 14, "a tablespoon", True),
        ("Beans, black, mature seeds, cooked, boiled, without salt", 172, "a cup, cooked", True),
        ("Snacks, pretzels, hard, plain, salted", 54, "9 pretzels", False),
    ]),
    ("set3", [
        ("Apples, raw, with skin", 182, "1 apple", True),
        ("Tomatoes, red, ripe, raw, year round average", 246, "2 tomatoes", True),
        ("Quinoa, cooked", 185, "a cup, cooked", True),
        ("Bread, white, commercially prepared", 30, "1 slice", False),
        ("Fish, salmon, Atlantic, farmed, cooked, dry heat", 150, "a fillet, cooked", False),
        ("Yogurt, Greek, plain, nonfat", 170, "a pot", True),
        ("Avocados, raw, California", 136, "1 avocado", True),
        ("Edamame, frozen, prepared", 155, "a cup, podded", True),
        ("Dates, medjool", 72, "3 dates", True),
    ]),
    ("set4", [
        ("Watermelon, raw", 154, "a cup, cubed", True),
        ("Corn, sweet, yellow, cooked, boiled, drained, without salt", 103, "1 cob", True),
        ("Pasta, cooked, enriched, with added salt", 124, "a cup, cooked", True),
        ("Snacks, granola bars, hard, plain", 42, "2 bars", True),
        ("Turkey, breast, smoked, lemon pepper flavor, 97% fat-free", 112, "4 slices", True),
        ("Milk, whole, 3.25% milkfat, with added vitamin D", 244, "a glass", True),
        ("Peanut Butter, smooth", 32, "2 tablespoons", True),
        ("Hummus, commercial", 80, "a bowl", False),
        ("Snacks, popcorn, air-popped", 24, "3 cups", True),
    ]),
]

# What the player is shown as the food's name. USDA descriptions are written for
# a database — "Bananas, raw", "Snacks, popcorn, air-popped" — and reading one of
# those on a photograph of a banana is absurd.
SHORT = {
    "Strawberries, raw": "strawberries",
    "Carrots, raw": "carrots",
    "Rice, white, long-grain, regular, cooked, enriched, with salt": "white rice",
    "Bread, whole-wheat, commercially prepared": "wholemeal bread",
    "Chicken, broilers or fryers, breast, meat only, cooked, fried": "chicken breast",
    "Egg, whole, cooked, hard-boiled": "boiled egg",
    "Nuts, almonds": "almonds",
    "Lentils, raw": "dry lentils",
    "Candies, milk chocolate": "milk chocolate",
    "Bananas, raw": "banana",
    "Broccoli, raw": "broccoli",
    "Rice, brown, long-grain, cooked": "brown rice",
    "Bagels, wheat": "bagel",
    "Pork, cured, bacon, cooked, baked": "bacon",
    "Cheese, cheddar": "cheddar",
    "Oil, olive, salad or cooking": "olive oil",
    "Beans, black, mature seeds, cooked, boiled, without salt": "black beans",
    "Snacks, pretzels, hard, plain, salted": "pretzels",
    "Apples, raw, with skin": "apple",
    "Tomatoes, red, ripe, raw, year round average": "tomatoes",
    "Quinoa, cooked": "quinoa",
    "Bread, white, commercially prepared": "white bread",
    "Fish, salmon, Atlantic, farmed, cooked, dry heat": "salmon",
    "Yogurt, Greek, plain, nonfat": "greek yogurt",
    "Avocados, raw, California": "avocado",
    "Edamame, frozen, prepared": "edamame",
    "Dates, medjool": "dates",
    "Watermelon, raw": "watermelon",
    "Corn, sweet, yellow, cooked, boiled, drained, without salt": "sweetcorn",
    "Pasta, cooked, enriched, with added salt": "pasta",
    "Snacks, granola bars, hard, plain": "granola bars",
    "Turkey, breast, smoked, lemon pepper flavor, 97% fat-free": "turkey breast",
    "Milk, whole, 3.25% milkfat, with added vitamin D": "whole milk",
    "Peanut Butter, smooth": "peanut butter",
    "Hummus, commercial": "hummus",
    "Snacks, popcorn, air-popped": "popcorn",
}


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=RAW)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--width", type=int, default=512)
    a = ap.parse_args()
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        sys.exit("Pillow is needed: pip install pillow")
    foods = usda()
    os.makedirs(os.path.join(a.out, "img"), exist_ok=True)
    deck, missing = [], []
    for name, items in GRIDS:
        src = os.path.join(a.raw, name + ".png")
        if not os.path.exists(src):
            missing.append(src)
            continue
        for tile, (food, g, portion, sure) in zip(tiles(src, a.width), items):
            row = foods.get(food)
            if row is None:
                sys.exit("not in legacy.json: " + food)
            s = slug(food)
            tile.save(os.path.join(a.out, "img", s + ".jpg"),
                      "JPEG", quality=86, optimize=True, progressive=True)
            deck.append({"id": s, "name": SHORT.get(food, food), "portion": portion,
                         "g": g, "kcal": round(row[2] * g / 100.0), "sure": sure,
                         "usda": food})
    if missing:
        print("no grid at:\n  " + "\n  ".join(missing))
    if not deck:
        sys.exit("nothing to build")
    # Two foods a player cannot separate are not a question, and two they can
    # separate at a glance are not one either. The pairing lives in the site, but
    # the deck is checked here so a build cannot quietly produce a dead game.
    ks = sorted(d["kcal"] for d in deck)
    pairs = sum(1 for i, a in enumerate(ks) for b in ks[i + 1:] if 1.15 <= b / max(1, a) <= 3.0)
    with open(os.path.join(a.out, "deck.json"), "w") as f:
        json.dump({"note": "Generated photographs; USDA SR Legacy energy densities.",
                   "foods": deck}, f, separators=(",", ":"))
    kb = sum(os.path.getsize(os.path.join(a.out, "img", d["id"] + ".jpg")) for d in deck) // 1024
    print("wrote %d foods, %d KB of pictures" % (len(deck), kb))
    print("%d kcal, low to high: %d to %d" % (len(deck), ks[0], ks[-1]))
    print("%d playable pairs (between 1.15x and 3x apart)" % pairs)
    print("%d of %d portions read off the picture rather than asked for"
          % (sum(1 for d in deck if not d["sure"]), len(deck)))


if __name__ == "__main__":
    main()
