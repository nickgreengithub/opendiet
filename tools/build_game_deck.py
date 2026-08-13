#!/usr/bin/env python3
"""Build the calorie game's deck from Nutrition5k.

Nutrition5k (Thames et al., CVPR 2021, CC BY 4.0) is ~3.5k cafeteria plates
photographed from overhead on a turntable, weighed on a scale, with a
per-ingredient breakdown. That combination is what makes the game possible:
the calorie figure is measured rather than estimated, and the breakdown can
say where the calories actually came from.

    python3 tools/build_game_deck.py [--n 140] [--out data/game]

Writes data/game/deck.json and data/game/img/<dish>.jpg. Run it once and
commit the result: the site stays static and fetches nothing at runtime.

The photographs come from the rig's side cameras rather than its overhead one.
The overhead RealSense frame is 640x480 and dim, which is all the game ever had;
the four side cameras are 1920x1080, better lit, and shot from three quarters,
where the height of the food is visible — and height is most of what a calorie
guess is actually reading. They are H.264 of the turntable turning, so this needs
a decoder:

    pip install pillow numpy av

Pass --source overhead to build the old way, which needs neither av nor numpy.
"""
import argparse
import io
import json
import math
import os
import re
import sys
import urllib.request

BUCKET = "https://storage.googleapis.com/nutrition5k_dataset/nutrition5k_dataset"
CAFES = ("dish_metadata_cafe1.csv", "dish_metadata_cafe2.csv")

# A plate earns its place only if its own numbers agree with each other and it is
# worth guessing at. Nutrition5k carries some rows whose ingredient calories do
# not add up to the stated total, and some that are a scrap of lettuce on a tray.
MIN_KCAL, MAX_KCAL = 70, 1100
MIN_G, MAX_G = 45, 900
MIN_INGR = 2
SUM_TOL = 0.06

# What the plate is, taken from whichever ingredient carries most of its
# calories. Rough by nature — a plate is rarely one thing — but it is the honest
# way to ask which kinds of food an eye reads badly.
GROUPS = [
    ("meat & fish", ("chicken", "beef", "steak", "pork", "ham", "turkey", "fish",
                     "salmon", "tuna", "sardine", "shrimp", "sausage", "bacon", "lamb",
                     "meatball", "duck", "cod", "tilapia")),
    ("eggs & dairy", ("egg", "cheese", "yogurt", "milk", "cream")),
    ("bread & grains", ("rice", "pasta", "bread", "bagel", "pizza", "potato", "waffle",
                        "oat", "millet", "quinoa", "tortilla", "noodle", "wheat", "couscous",
                        "corn", "barley", "cereal", "pancake", "bun", "crouton", "cracker")),
    ("beans & pulses", ("lentil", "chickpea", "hummus", "black beans", "kidney", "tofu",
                        "edamame", "pinto", "garbanzo")),
    ("nuts & oils", ("oil", "butter", "nuts", "almond", "peanut", "avocado", "dressing",
                     "mayo", "tahini", "pesto", "seeds", "cashew", "walnut")),
    ("fruit", ("apple", "berry", "berries", "banana", "melon", "orange", "grape",
               "pineapple", "mango", "peach", "pear", "raisin")),
    ("vegetables", ("salad", "greens", "spinach", "broccoli", "carrot", "lettuce", "kale",
                    "chard", "tomato", "cucumber", "pepper", "squash", "zucchini",
                    "cauliflower", "mushroom", "onion", "asparagus", "beet", "pea",
                    "cabbage", "celery", "green beans")),
]


def category(name):
    n = (name or "").lower()
    for label, words in GROUPS:
        if any(w in n for w in words):
            return label
    return "mixed"


# What the player is really being asked to read. Fat hides in these — they are
# poured, melted or absorbed rather than plated, so they are the usual reason an
# eye is wrong about a tray.
HIDDEN_FAT = ("oil", "butter", "dressing", "mayo", "mayonnaise", "cheese", "cream",
              "fried", "bacon", "sausage", "peanut butter", "nuts", "almond",
              "avocado", "gravy", "syrup", "tahini", "pesto", "aioli", "ranch")


def fetch(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1:
                raise
    return None


def rows(csv_bytes):
    """Each line is: id, kcal, grams, fat, carb, protein, then groups of seven."""
    for line in csv_bytes.decode("utf-8", "replace").splitlines():
        f = line.split(",")
        if len(f) < 13 or not f[0].startswith("dish_"):
            continue
        try:
            dish = {"id": f[0], "kcal": float(f[1]), "g": float(f[2]),
                    "fat": float(f[3]), "carb": float(f[4]), "pro": float(f[5])}
        except ValueError:
            continue
        ingr = []
        i = 6
        while i + 6 < len(f):
            try:
                ingr.append({"name": f[i + 1].strip().lower(), "g": float(f[i + 2]),
                             "kcal": float(f[i + 3])})
            except ValueError:
                pass
            i += 7
        dish["ingr"] = ingr
        yield dish


def keep(d):
    if not (MIN_KCAL <= d["kcal"] <= MAX_KCAL and MIN_G <= d["g"] <= MAX_G):
        return False
    ingr = [x for x in d["ingr"] if x["g"] > 0 and x["name"]]
    if len(ingr) < MIN_INGR:
        return False
    # The breakdown is the whole payload, so it has to agree with the total.
    s = sum(x["kcal"] for x in ingr)
    if s <= 0 or abs(s - d["kcal"]) / d["kcal"] > SUM_TOL:
        return False
    d["ingr"] = ingr
    return True


def shares(d):
    """The plate's own numbers, as fractions of its energy."""
    k = max(1.0, d["kcal"])
    return ((d["fat"] * 9.0) / k, (d["carb"] * 4.0) / k, (d["pro"] * 4.0) / k)


def tag(d, light_at, dense_at):
    """Why an eye gets a plate wrong, in the plate's own numbers.

    Density is the single most explanatory variable: a calorie is easy to see
    when it arrives with bulk and invisible when it does not, which is why a
    dressed salad reads lighter than it is. The bands are the deck's own
    tertiles rather than round numbers, so each holds a third of the plates and
    the readout at the end has something to compare. A plate is 'dressed' only
    when fat is genuinely carrying it — nearly every cafeteria tray has some oil
    in it somewhere, so the ingredient names alone said nothing.
    """
    dens = d["kcal"] / max(1.0, d["g"])
    fat_share, carb_share, pro_share = shares(d)
    names = " ".join(x["name"] for x in d["ingr"])
    tags = ["dense" if dens >= dense_at else "light" if dens <= light_at else "middling"]
    if fat_share >= 0.45 or (fat_share >= 0.35 and any(w in names for w in HIDDEN_FAT)):
        tags.append("dressed")
    if pro_share >= 0.30 and fat_share < 0.28:
        tags.append("lean")
    return tags, round(dens, 3)


def plate_box(dep, w, h):
    """Where the plate is, from the dish's own depth map.

    The turntable is whatever depth most pixels share; the plate and the food
    stand proud of it. Reading the box per dish rather than cropping to a fixed
    rectangle is what makes the zoom safe — no two plates sit in quite the same
    place. The box is drawn around the plate and not the food, because the plate
    is the size reference the whole guess rests on.
    """
    import collections
    px = dep.load()
    hist = collections.Counter()
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            v = px[x, y]
            if 1000 < v < 20000:
                hist[v // 25 * 25] += 1
    if not hist:
        return None
    table = hist.most_common(1)[0][0]
    thr = table - 60  # about 6mm proud: enough to catch the rim of the plate
    xs, ys = [], []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            v = px[x, y]
            if 1000 < v < thr:
                xs.append(x)
                ys.append(y)
    if len(xs) < 200:
        return None
    xs.sort()
    ys.sort()
    # Trim the outer 2% so one stray reading on the rig cannot drag the box out.
    k = max(1, len(xs) // 50)
    return xs[k], ys[k], xs[-k], ys[-k]


def framed(rgb, dep, out_w, out_h):
    """Crop to the plate at the output's aspect, then lift the exposure.

    The RealSense underexposes — across the deck the 99th percentile of luma
    sits near 215 of 255, where a well-exposed frame reaches 250 — and the dark
    rig around the plate was doing the rest of the damage. Cropping removes most
    of the gloom; the level stretch takes care of what is left.
    """
    from PIL import Image, ImageEnhance, ImageOps
    w, h = rgb.size
    box = plate_box(dep, w, h) if dep else None
    if box:
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        bw, bh = (x1 - x0) * 1.02, (y1 - y0) * 1.02   # a hair of air around the rim
        ar = out_w / float(out_h)
        cw = max(bw, bh * ar)
        ch = cw / ar
        if ch < bh:
            ch = bh
            cw = ch * ar
        cw, ch = min(cw, w), min(ch, h)
        x = max(0, min(w - cw, cx - cw / 2))
        y = max(0, min(h - ch, cy - ch / 2))
        rgb = rgb.crop((int(x), int(y), int(x + cw), int(y + ch)))
    rgb = rgb.resize((out_w, out_h), Image.LANCZOS)
    return exposed(rgb)


# Camera A looks down on the plate at a slight angle — near enough overhead to
# read the spread of the food, angled enough to show its height. B and C sit low
# and catch more of the rig than the plate, so they are never used; D is a wider
# three-quarter view, kept for the dishes where A returned nothing usable.
SIDE_CAMS = ("A", "D")
SIDE_ENOUGH = 800      # a score A has to clear before D is not even fetched
SIDE_BYTES = 6000000   # about half the turn, which is all the rotation we need
SIDE_EVERY = 3         # every third frame: the turntable is not moving fast
MW, MH = 192, 108      # the scale the frame is judged at, which is plenty


def _dense(m, thr=0.5):
    """Keep only mask pixels with company, so speckle and colour fringing go."""
    import numpy as np
    p = np.pad(m.astype(np.float32), 1, mode="constant")
    acc = np.zeros(m.shape, dtype=np.float32)
    for dy in range(3):
        for dx in range(3):
            acc += p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    return m & (acc / 9.0 >= thr)


def frame_score(im, ar):
    """How well this rotation of the turntable suits a fixed crop.

    The rig does not move and neither does the plate on it, so the crop can be
    fixed — a full-height window of the output's aspect, in the middle of the
    frame. What does move is the food, which sits wherever it was plated and
    comes round with the turntable. So the frame is what gets chosen: the one
    with the most food inside that window and the least hanging out of it. Food
    is read as colour, because the china is white and the table is dark glass;
    that mistakes a coloured plate for food, but only ever by counting the whole
    plate, which is centred anyway and so does not move the answer.
    """
    import numpy as np
    a = np.asarray(im.resize((MW, MH)).convert("HSV"), dtype=np.float32)
    s, v = a[..., 1] / 255.0, a[..., 2] / 255.0
    food = _dense((s > 0.34) & (v > 0.22) & (v < 0.99), 0.6)
    total = food.sum()
    if total < 40:
        return -1e9
    half = MH * ar / 2.0
    inside = food[:, int(MW / 2 - half):int(MW / 2 + half)].sum()
    return inside - 2.2 * (total - inside)


def side_photo(dish, out_w, out_h):
    """The best frame of the best side camera, cropped to the fixed window."""
    import av
    from PIL import Image
    ar = out_w / float(out_h)
    tmp = os.path.join(os.path.dirname(__file__), ".side.h264")
    best_score, best_im = -1e9, None
    for cam in SIDE_CAMS:
        url = "%s/imagery/side_angles/%s/camera_%s.h264" % (BUCKET, dish, cam)
        try:
            req = urllib.request.Request(url, headers={"Range": "bytes=0-%d" % SIDE_BYTES})
            with open(tmp, "wb") as f:
                f.write(urllib.request.urlopen(req, timeout=180).read())
            stream = av.open(tmp, format="h264")
        except Exception:
            continue
        try:
            n = 0
            for f in stream.decode(video=0):
                n += 1
                if n % SIDE_EVERY:
                    continue
                im = f.to_image()
                sc = frame_score(im, ar)
                if sc > best_score:
                    best_score, best_im = sc, im
        except Exception:
            pass
        # A camera that framed the plate well is the end of it; the second one
        # is for the dishes where the food spent the whole turn out of shot.
        if best_score > SIDE_ENOUGH:
            break
    if os.path.exists(tmp):
        os.remove(tmp)
    if best_im is None:
        return None
    W, H = best_im.size
    w = min(W, H * ar)
    h = w / ar
    x = (W - w) / 2.0
    y = (H - h) / 2.0
    im = best_im.crop((int(x), int(y), int(x + w), int(y + h)))
    # These frames start far better exposed than the overhead one, so they are
    # brought to a lower mark: lifting them as hard would wash the plate out.
    return exposed(im.resize((out_w, out_h), Image.LANCZOS), 168.0)


def exposed(rgb, target=186.0):
    """Bring every plate to the same brightness without bleaching the china.

    One gamma cannot serve the whole deck. The frames run from dim to nearly
    right, and about a seventh of each one is white plate already sitting at the
    top of the scale, so a flat gain blows the china long before the food gets
    anywhere. So the curve is chosen per image — as much gamma as it takes to put
    that image's own median luma on `target` — and then rolled off towards the
    identity as a pixel approaches white, which is exactly where the plate lives.
    The black point is trimmed first, from the bottom only, so the lift has
    somewhere to come from and the result does not go milky.
    """
    from PIL import ImageEnhance, ImageOps
    rgb = ImageOps.autocontrast(rgb, cutoff=(0.5, 0.0))
    hist = rgb.convert("L").histogram()
    n, acc, med = sum(hist), 0, 128
    for v, c in enumerate(hist):
        acc += c
        if acc >= n * 0.5:
            med = max(8, min(250, v))
            break
    g = max(0.38, min(1.0, math.log(target / 255.0) / math.log(med / 255.0)))
    lut = []
    for v in range(256):
        x = v / 255.0
        keep = x ** 3                      # near white, the plate is left as shot
        lut.append(int(round(255 * ((x ** g) * (1 - keep) + x * keep))))
    out = rgb.point(lut * 3)
    out = ImageEnhance.Color(out).enhance(1.14)
    return ImageEnhance.Contrast(out).enhance(1.05)


def top_ingredients(d, n=3):
    """The two or three that dominate, as a share of the total."""
    ranked = sorted(d["ingr"], key=lambda x: -x["kcal"])[:n]
    out = []
    for x in ranked:
        share = x["kcal"] / d["kcal"]
        if share < 0.04 and out:
            break
        out.append([x["name"], round(x["g"]), round(x["kcal"]), round(share, 3)])
    return out


def spread(cands, n):
    """Take a deck across the calorie range rather than a pile of 300 kcal trays."""
    bands = [(70, 200), (200, 320), (320, 450), (450, 620), (620, 1100)]
    per = max(1, n // len(bands))
    picked, seen = [], set()
    for lo, hi in bands:
        band = [d for d in cands if lo <= d["kcal"] < hi]
        # Evenly through the band rather than the first however many.
        step = max(1, len(band) // per)
        for d in band[::step][:per]:
            if d["id"] not in seen:
                seen.add(d["id"])
                picked.append(d)
    for d in cands:
        if len(picked) >= n:
            break
        if d["id"] not in seen:
            seen.add(d["id"])
            picked.append(d)
    return picked[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=140)
    ap.add_argument("--out", default="data/game")
    ap.add_argument("--width", type=int, default=900)
    ap.add_argument("--quality", type=int, default=80)
    ap.add_argument("--source", choices=("side", "overhead"), default="side")
    a = ap.parse_args()

    cands = []
    for cafe in CAFES:
        print("reading", cafe, flush=True)
        for d in rows(fetch(BUCKET + "/metadata/" + cafe)):
            if keep(d):
                cands.append(d)
    cands.sort(key=lambda d: d["id"])
    print("%d plates pass the filters" % len(cands))

    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow is needed to prepare the photographs: pip install pillow")

    img_dir = os.path.join(a.out, "img")
    os.makedirs(img_dir, exist_ok=True)
    chosen, want = [], spread(cands, int(a.n * 1.35))
    for d in want:
        if len(chosen) >= a.n:
            break
        dest = os.path.join(img_dir, d["id"] + ".jpg")
        # A second run only re-reads the numbers; the photographs stay put.
        if not os.path.exists(dest):
            out_h = int(a.width * 4 / 5)
            if a.source == "side":
                # Not every dish was filmed from the side — about a twentieth
                # were not — and one that was not simply does not make the deck.
                try:
                    im = side_photo(d["id"], a.width, out_h)
                except ImportError:
                    sys.exit("The side cameras need a decoder: pip install av numpy")
                if im is None:
                    continue
            else:
                base = "%s/imagery/realsense_overhead/%s/" % (BUCKET, d["id"])
                try:
                    im = Image.open(io.BytesIO(fetch(base + "rgb.png", tries=2))).convert("RGB")
                except Exception:
                    continue
                try:
                    dep = Image.open(io.BytesIO(fetch(base + "depth_raw.png", tries=2)))
                except Exception:
                    dep = None
                im = framed(im, dep, a.width, out_h)
            im.save(dest, "JPEG", quality=a.quality, optimize=True, progressive=True)
            if len(chosen) % 20 == 0:
                print("  %d photographs" % len(chosen), flush=True)
        chosen.append(d)

    # The density bands are the deck's own tertiles, so each holds a third.
    dl = sorted(x["kcal"] / max(1.0, x["g"]) for x in chosen)
    light_at, dense_at = dl[len(dl) // 3], dl[2 * len(dl) // 3]
    print("density bands: light <= %.2f, dense >= %.2f kcal/g" % (light_at, dense_at))
    deck = []
    for d in chosen:
        tags, dens = tag(d, light_at, dense_at)
        # The macro shares stay out of the deck deliberately: Nutrition5k's
        # per-macro figures do not always agree with the plate's own total, so
        # they are sound enough to sort plates by and not sound enough to show.
        # Names only, and every one of them: the player is told what is on the
        # plate and asked to judge how much of it there is.
        names, seen = [], set()
        for x in sorted(d["ingr"], key=lambda y: -y["kcal"]):
            nm = x["name"]
            if nm not in seen:
                seen.add(nm)
                names.append(nm)
        top = top_ingredients(d)
        # Everything outside the three that dominate, gathered so the breakdown
        # adds up to the plate rather than trailing off.
        shown = set(x[0] for x in top)
        others = [x for x in d["ingr"] if x["name"] not in shown]
        rest = [round(sum(x["g"] for x in others)), round(sum(x["kcal"] for x in others)),
                len(others)] if others else None
        deck.append({"id": d["id"], "kcal": round(d["kcal"]), "g": round(d["g"]),
                     "dens": dens, "tags": tags, "top": top, "rest": rest,
                     "cat": category(top[0][0] if top else ""),
                     "of": names[:9]})

    deck.sort(key=lambda x: x["kcal"])
    out = {
        "source": "Nutrition5k — Thames et al., CVPR 2021. CC BY 4.0.",
        "note": "US cafeteria plates on consistent crockery, photographed overhead.",
        "count": len(deck),
        "dishes": deck,
    }
    with open(os.path.join(a.out, "deck.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    kb = sum(os.path.getsize(os.path.join(img_dir, f)) for f in os.listdir(img_dir)) // 1024
    print("wrote %d dishes, %d KB of photographs" % (len(deck), kb))


if __name__ == "__main__":
    main()
