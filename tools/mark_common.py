#!/usr/bin/env python3
"""Mark the everyday foods in each library so search can float them to the top.

USDA names a plain apple `Apples, raw, with skin` and sorts it below
`Apple juice, canned or bottled, unsweetened, with added ascorbic acid`. Someone
typing "apple" wants the apple. This tags the entry a shopper would mean for each
of a list of staples, and writes the flag as an eleventh element on the food row:

    [name, catIdx, kcal, p, c, fibre, fat, satfat, sugar, liquid, common]

Older readers stop at index 9, so the file stays backwards compatible.

    python3 tools/mark_common.py            # rewrite data/*.json in place
    python3 tools/mark_common.py --dry-run  # print what would be marked

A rule is (label, must, prefer, avoid, n): every `must` substring has to appear in
the name, no `avoid` substring may, and among the survivors the entries with the
most `prefer` hits and the plainest name win. `n` is how many to keep — two when
both the raw and the cooked form are things people actually look up.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBS = ["core", "legacy", "survey"]

# Names get longer as they get more processed, so plainness is mostly a matter of
# counting qualifiers. These are the words that mean "not what a shopper meant".
NOISE = [
    "dehydrated", "sulfured", "concentrate", "undiluted", "reconstituted", "imitation",
    "substitute", "powder", "freeze-dried", "instant", "restaurant", "baby food",
    "infant", "formula", "low moisture", "home-prepared", "commercially", "nfs",
    "not further specified", "extruded", "hydrolyzed", "spread", "syrup", "packed in",
    "glaze", "breaded", "battered", "dry mix", "unprepared", "with added solution",
    "mechanically separated", "variety meats", "by-products", "reduced sodium",
    "low calorie sweetener", "fortified", "flavored", "flavor", "supplement",
]


def plainness(name):
    low = name.lower()
    s = 10.0
    s -= low.count(",") * 1.4
    s -= len(name) / 45.0
    s -= 1.0 * low.count("(")
    for w in NOISE:
        if w in low:
            s -= 2.5
    return s


# label, must, prefer, avoid, how many to keep
RULES = [
    # fruit
    ("apple", ["apples", "raw"], ["with skin"], ["juice", "dried", "fuji", "gala", "delicious", "granny"], 1),
    ("banana", ["bananas", "raw"], [], ["dried"], 1),
    ("orange", ["oranges", "raw"], ["all commercial"], ["juice", "peel"], 1),
    ("strawberry", ["strawberries", "raw"], [], ["frozen"], 1),
    ("blueberry", ["blueberries", "raw"], [], ["frozen", "wild"], 1),
    ("raspberry", ["raspberries", "raw"], [], ["frozen"], 1),
    ("blackberry", ["blackberries", "raw"], [], ["frozen"], 1),
    ("grape", ["grapes", "raw"], ["red or green"], ["juice"], 1),
    ("pear", ["pears", "raw"], [], ["dried", "canned", "juice"], 1),
    ("peach", ["peaches", "raw"], [], ["canned", "dried", "frozen"], 1),
    ("plum", ["plums", "raw"], [], ["dried", "canned"], 1),
    ("cherry", ["cherries", "raw"], ["sweet"], ["canned", "frozen", "maraschino"], 1),
    ("pineapple", ["pineapple", "raw"], [], ["canned", "juice", "dried"], 1),
    ("mango", ["mangos", "raw"], [], ["dried"], 1),
    ("melon", ["melons", "raw"], ["cantaloupe"], [], 1),
    ("watermelon", ["watermelon", "raw"], [], [], 1),
    ("kiwi", ["kiwifruit", "raw"], [], [], 1),
    ("avocado", ["avocados", "raw"], ["california"], [], 1),
    ("lemon", ["lemons", "raw"], [], ["juice", "peel"], 1),
    ("lime", ["limes", "raw"], [], ["juice"], 1),
    ("grapefruit", ["grapefruit", "raw"], [], ["juice"], 1),
    ("apricot", ["apricots", "raw"], [], ["dried", "canned"], 1),
    ("fig", ["figs", "raw"], [], ["dried"], 1),
    ("date", ["dates"], ["deglet noor"], ["dried"], 1),
    ("olive", ["olives"], ["ripe", "canned"], [], 1),
    ("raisin", ["raisins"], ["seedless"], ["golden"], 1),
    ("cranberry", ["cranberries", "raw"], [], ["juice", "sauce", "dried"], 1),
    ("pomegranate", ["pomegranate", "raw"], [], ["juice"], 1),
    # vegetables
    ("potato", ["potatoes", "raw"], ["flesh and skin"], ["sweet", "red", "russet", "white"], 1),
    ("potato baked", ["potatoes", "baked", "flesh and skin"], ["without salt"], [], 1),
    ("sweet potato", ["sweet potato", "raw"], [], ["leaves", "puffs", "canned"], 1),
    ("carrot", ["carrots", "raw"], [], ["baby", "canned", "frozen", "juice"], 1),
    ("broccoli", ["broccoli", "raw"], [], ["frozen", "raab", "chinese"], 1),
    ("broccoli cooked", ["broccoli", "cooked", "boiled"], ["without salt"], ["frozen", "raab", "chinese"], 1),
    ("tomato", ["tomatoes", "red", "raw"], ["year round average"], ["canned", "juice", "sun-dried", "green"], 1),
    ("onion", ["onions", "raw"], [], ["spring", "welsh", "dehydrated", "young green"], 1),
    ("garlic", ["garlic", "raw"], [], ["powder"], 1),
    ("spinach", ["spinach", "raw"], [], ["canned", "frozen", "mustard", "new zealand"], 1),
    ("kale", ["kale", "raw"], [], ["frozen", "scotch"], 1),
    ("lettuce", ["lettuce", "raw"], ["cos or romaine"], [], 1),
    ("cucumber", ["cucumber", "raw"], ["with peel"], [], 1),
    ("pepper", ["peppers", "sweet", "red", "raw"], [], ["frozen", "canned", "freeze-dried"], 1),
    ("mushroom", ["mushrooms", "raw"], ["white"], ["canned", "dried"], 1),
    ("courgette", ["squash", "summer", "zucchini", "raw"], ["includes skin"], [], 1),
    ("aubergine", ["eggplant", "raw"], [], [], 1),
    ("cauliflower", ["cauliflower", "raw"], [], ["frozen", "green"], 1),
    ("cabbage", ["cabbage", "raw"], [], ["red", "savoy", "chinese", "napa"], 1),
    ("celery", ["celery", "raw"], [], [], 1),
    ("green beans", ["beans", "snap", "green", "raw"], [], ["canned", "frozen"], 1),
    ("peas", ["peas", "green", "raw"], [], ["canned", "frozen", "split", "edible-podded"], 1),
    ("sweetcorn", ["corn", "sweet", "yellow", "raw"], [], ["canned", "frozen"], 1),
    ("asparagus", ["asparagus", "raw"], [], ["canned", "frozen"], 1),
    ("beetroot", ["beets", "raw"], [], ["canned", "greens"], 1),
    ("pumpkin", ["pumpkin", "raw"], [], ["canned", "flowers", "leaves"], 1),
    ("butternut squash", ["squash", "winter", "butternut", "raw"], [], ["frozen"], 1),
    ("leek", ["leeks", "raw"], [], ["freeze-dried"], 1),
    ("brussels sprouts", ["brussels sprouts", "raw"], [], ["frozen"], 1),
    # grains and starches
    ("rice white", ["rice", "white", "long-grain", "regular", "cooked"], ["unenriched"], ["instant", "parboiled"], 1),
    ("rice white raw", ["rice", "white", "long-grain", "regular", "raw"], ["unenriched"], ["instant", "parboiled"], 1),
    ("rice brown", ["rice", "brown", "long-grain", "cooked"], [], [], 1),
    ("oats", ["oats"], [], ["bran", "flour"], 1),
    ("pasta", ["pasta", "cooked"], ["unenriched", "without added salt"], ["homemade", "gluten-free", "corn", "whole-wheat", "fresh"], 1),
    ("pasta wholemeal", ["pasta", "whole-wheat", "cooked"], [], [], 1),
    ("bread white", ["bread", "white", "commercially prepared"], [], ["reduced calorie", "toasted"], 1),
    ("bread wholemeal", ["bread", "whole-wheat", "commercially prepared"], [], ["toasted"], 1),
    ("quinoa", ["quinoa", "cooked"], [], [], 1),
    ("couscous", ["couscous", "cooked"], [], [], 1),
    ("barley", ["barley", "pearled", "cooked"], [], [], 1),
    ("buckwheat", ["buckwheat groats", "cooked"], [], [], 1),
    ("cornflour", ["cornmeal"], ["whole-grain", "yellow"], [], 1),
    ("flour", ["wheat flour", "white", "all-purpose"], ["unenriched"], ["bleached", "self-rising", "cake"], 1),
    ("tortilla", ["tortillas", "ready-to-bake"], ["corn"], [], 1),
    # legumes
    ("lentils", ["lentils", "raw"], [], ["sprouted"], 1),
    ("lentils cooked", ["lentils", "cooked", "boiled"], ["without salt"], ["sprouted"], 1),
    ("chickpeas", ["chickpeas", "cooked"], ["without salt"], ["canned"], 1),
    ("chickpeas raw", ["chickpeas", "raw"], [], [], 1),
    ("black beans", ["beans", "black", "cooked"], ["without salt"], ["canned"], 1),
    ("kidney beans", ["beans", "kidney", "red", "cooked"], ["without salt"], ["canned"], 1),
    ("baked beans", ["beans", "baked", "canned"], ["plain or vegetarian"], ["beef", "pork"], 1),
    ("soybeans", ["soybeans", "cooked"], ["without salt"], [], 1),
    ("edamame", ["edamame"], ["frozen", "prepared"], [], 1),
    ("tofu", ["tofu", "raw"], ["firm"], ["fried", "salted", "yogurt", "okara"], 1),
    ("peanut butter", ["peanut butter", "smooth"], [], ["reduced", "vitamin"], 1),
    ("hummus", ["hummus"], ["commercial"], [], 1),
    # nuts and seeds
    ("almonds", ["nuts", "almonds"], ["raw"], ["butter", "oil", "milk", "flour", "blanched"], 1),
    ("walnuts", ["nuts", "walnuts", "english"], [], ["oil"], 1),
    ("cashews", ["nuts", "cashew nuts", "raw"], [], ["butter", "oil"], 1),
    ("pistachio", ["nuts", "pistachio nuts", "raw"], [], [], 1),
    ("hazelnut", ["nuts", "hazelnuts"], [], ["oil", "butter"], 1),
    ("brazil nuts", ["nuts", "brazilnuts"], [], [], 1),
    ("pecans", ["nuts", "pecans"], [], ["oil"], 1),
    ("coconut", ["nuts", "coconut meat", "raw"], [], ["dried", "milk", "water", "cream"], 1),
    ("chia", ["seeds", "chia seeds", "dried"], [], [], 1),
    ("flaxseed", ["seeds", "flaxseed"], [], ["oil"], 1),
    ("sunflower seeds", ["seeds", "sunflower seed kernels"], ["dried"], ["butter", "oil", "toasted"], 1),
    ("pumpkin seeds", ["seeds", "pumpkin and squash seed kernels"], ["dried"], ["roasted"], 1),
    ("sesame", ["seeds", "sesame seeds"], ["whole", "dried"], ["butter", "oil", "flour"], 1),
    # dairy and eggs
    ("milk whole", ["milk", "whole", "3.25% milkfat"], ["with added vitamin d"], [], 1),
    ("milk semi", ["milk", "reduced fat", "fluid", "2% milkfat"], ["with added vitamin a and vitamin d"], [], 1),
    ("milk skimmed", ["milk", "nonfat", "fluid"], ["with added vitamin a and vitamin d"], ["dry", "calcium"], 1),
    ("yogurt plain", ["yogurt", "plain", "whole milk"], [], ["greek"], 1),
    ("greek yogurt", ["yogurt", "greek", "plain", "nonfat"], [], [], 1),
    ("greek yogurt whole", ["yogurt", "greek", "plain", "whole milk"], [], [], 1),
    ("cheddar", ["cheese", "cheddar"], [], ["reduced fat", "nonfat", "low", "sharp", "processed"], 1),
    ("mozzarella", ["cheese", "mozzarella", "whole milk"], [], ["low moisture", "part skim"], 1),
    ("feta", ["cheese", "feta"], [], [], 1),
    ("parmesan", ["cheese", "parmesan"], ["grated"], ["hard", "shredded", "low sodium"], 1),
    ("cottage cheese", ["cheese", "cottage", "creamed", "large or small curd"], [], [], 1),
    ("cream cheese", ["cheese", "cream"], [], ["low fat", "fat free", "whipped"], 1),
    ("butter", ["butter", "salted"], ["without"], ["whipped", "oil", "light"], 1),
    ("egg", ["egg", "whole", "raw", "fresh"], [], [], 1),
    ("egg boiled", ["egg", "whole", "cooked", "hard-boiled"], [], [], 1),
    ("egg white", ["egg", "white", "raw", "fresh"], [], [], 1),
    # meat and fish
    ("chicken breast", ["chicken", "breast", "meat only"], ["cooked", "roasted"], ["tenders", "roll", "sliced", "canned", "oscar"], 1),
    ("chicken breast raw", ["chicken", "breast", "meat only", "raw"], [], ["tenders", "roll", "sliced", "oscar"], 1),
    ("chicken thigh", ["chicken", "thigh", "meat only"], ["cooked"], ["oscar"], 1),
    ("chicken whole", ["chicken", "broilers or fryers", "meat only", "raw"], [], ["giblets"], 1),
    ("turkey", ["turkey", "breast", "meat only"], ["cooked", "roasted"], ["prepackaged", "sliced", "deli"], 1),
    ("beef mince", ["beef", "ground", "90% lean"], [], [], 1),
    ("beef steak", ["beef", "loin", "top sirloin", "separable lean only"], ["cooked", "broiled"], [], 1),
    ("pork chop", ["pork", "loin", "separable lean only", "cooked"], [], [], 1),
    ("bacon", ["pork", "bacon", "cooked"], [], ["canadian", "turkey", "meatless", "rendered fat"], 1),
    ("lamb", ["lamb", "separable lean only", "cooked"], [], [], 1),
    ("salmon", ["fish", "salmon", "atlantic"], ["cooked"], ["smoked", "canned", "nuggets"], 1),
    ("salmon raw", ["fish", "salmon", "atlantic", "raw"], [], ["smoked"], 1),
    ("tuna", ["fish", "tuna", "light", "canned in water"], ["drained solids"], [], 1),
    ("tuna raw", ["fish", "tuna", "fresh", "raw"], ["yellowfin"], [], 1),
    ("cod", ["fish", "cod", "atlantic", "raw"], [], ["dried", "canned"], 1),
    ("prawns", ["crustaceans", "shrimp"], ["raw"], ["breaded", "canned", "imitation"], 1),
    ("sardines", ["fish", "sardine", "canned in oil"], ["drained solids"], [], 1),
    ("mackerel", ["fish", "mackerel", "atlantic", "raw"], [], ["salted", "smoked"], 1),
    # fats, sugars, drinks
    ("olive oil", ["oil", "olive", "salad or cooking"], [], ["olives", "loaf", "mayonnaise", "blend"], 1),
    ("rapeseed oil", ["oil", "canola"], [], ["industrial", "blend"], 1),
    ("sunflower oil", ["oil", "sunflower"], ["linoleic"], ["seeds", "kernels", "industrial", "blend"], 1),
    ("coconut oil", ["oil", "coconut"], [], ["industrial", "meat", "milk", "water", "blend"], 1),
    ("sugar", ["sugars", "granulated"], [], ["brown", "powdered"], 1),
    ("honey", ["honey"], [], ["sausage", "roll", "ham", "roasted", "cereal", "babyfood", "graham", "mustard", "loaf", "nut"], 1),
    ("maple syrup", ["syrups", "maple"], [], [], 1),
    ("dark chocolate", ["chocolate", "dark", "70-85%"], [], [], 1),
    ("milk chocolate", ["candies", "milk chocolate"], [], ["coated", "with"], 1),
    ("coffee", ["beverages", "coffee", "brewed"], ["prepared with tap water"], ["instant", "decaffeinated", "espresso"], 1),
    ("tea", ["beverages", "tea", "brewed", "prepared with tap water"], [], ["herb", "instant", "decaffeinated", "green"], 1),
    ("orange juice", ["orange juice", "raw"], [], ["frozen", "canned"], 1),
    ("water", ["beverages", "water", "tap", "drinking"], [], [], 1),
]


def pick(names, must, prefer, avoid, n):
    out = []
    for name in names:
        low = name.lower()
        if any(m not in low for m in must):
            continue
        if any(a in low for a in avoid):
            continue
        out.append(name)
    if not out:
        return []
    out.sort(key=lambda nm: (-sum(p in nm.lower() for p in prefer), -plainness(nm), nm))
    return out[:n]


def mark(lib, dry):
    path = ROOT / "data" / f"{lib}.json"
    d = json.loads(path.read_text())
    names = [f[0] for f in d["foods"]]
    chosen, misses = {}, []
    for label, must, prefer, avoid, n in RULES:
        if n == 0:
            continue
        hits = pick(names, must, prefer, avoid, n)
        if not hits:
            misses.append(label)
        for h in hits:
            chosen.setdefault(h, label)
    for f in d["foods"]:
        common = 1 if f[0] in chosen else 0
        if len(f) >= 11:
            f[10] = common
        elif common:
            f.append(common)
    if not dry:
        path.write_text(json.dumps(d, separators=(",", ":")))
    return chosen, misses


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    for lib in LIBS:
        chosen, misses = mark(lib, dry)
        print(f"\n=== {lib}: {len(chosen)} marked, {len(misses)} rules with no match")
        if misses:
            print("    no match:", ", ".join(misses))
        if lib == "core" or "-v" in sys.argv:
            for name, label in sorted(chosen.items(), key=lambda kv: kv[1]):
                print(f"    {label:<20} {name}")
    print("\ndry run, nothing written" if dry else "\nwritten")
