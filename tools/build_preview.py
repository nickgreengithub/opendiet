#!/usr/bin/env python3
"""Fold the site into one file, so a branch can be looked at without being deployed.

GitHub Pages serves one site per repository and this one serves `main`, so a branch has
nowhere to be seen. This writes a single self-contained page that can be: every script,
stylesheet and library inlined, and the food libraries carried inside it rather than
fetched. Nothing about the app changes — the same index.html, the same support.js, the
same data — so what you look at is what the branch does.

Three substitutions, and they are the whole of it:

  · React and Babel are pulled from a content-delivery network the host allows;
  · fetch() for a data file is answered from the copy already in the page;
  · the document wrapper comes off, since the host supplies its own.

    python3 tools/build_preview.py                       # writes preview.html
    python3 tools/build_preview.py --out /tmp/beta.html  # somewhere else
    python3 tools/build_preview.py --lib legacy          # one library, a smaller file
"""
import argparse
import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# unpkg is not on the host's allowlist; cdnjs is, and carries the same UMD builds.
CDN = {
    "https://unpkg.com/react@18.3.1/umd/react.production.min.js":
        "https://cdnjs.cloudflare.com/ajax/libs/react/18.3.1/umd/react.production.min.js",
    "https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js":
        "https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.3.1/umd/react-dom.production.min.js",
    "https://unpkg.com/@babel/standalone@7.29.0/babel.min.js":
        "https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.29.0/babel.min.js",
}


def guard(text):
    """A script inlined into a page must not carry the string that would end it early."""
    return text.replace("</script", "<\\/script")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "preview.html"))
    ap.add_argument("--lib", action="append", help="a library to carry; repeatable")
    args = ap.parse_args()
    libs = args.lib or ["legacy", "core", "survey"]

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    support = (ROOT / "support.js").read_text(encoding="utf-8")
    for old, new in CDN.items():
        support = support.replace(old, new)
    # support.js names the element it looks for, in a string and in a regex, and finds the
    # template by scanning the page text for it. Inlined as it stands, it puts an <x-dc>
    # into the page ahead of the real one and the app parses itself instead of the app.
    # The letter is written as an escape: the same string to JavaScript, the same character
    # class to a regex, and nothing a scan of the text can see.
    support = support.replace("x-dc", "x-\\u0064c")

    parts = []
    # The libraries, and a fetch that answers from them. The app asks for "data/legacy.json"
    # and gets the object it would have parsed, so nothing downstream knows the difference.
    data = {f"data/{k}.json": json.loads((ROOT / "data" / f"{k}.json").read_text())
            for k in libs}
    parts.append("<script>window.__OD_DATA = " + guard(json.dumps(data, separators=(",", ":")))
                 + ";\n(function () { var real = window.fetch;\n"
                 "  window.fetch = function (u) {\n"
                 "    var hit = window.__OD_DATA[String(u).replace(/^\\.\\//, \"\")];\n"
                 "    if (!hit) return real.apply(this, arguments);\n"
                 "    return Promise.resolve({ ok: true, status: 200,\n"
                 "      json: function () { return Promise.resolve(hit); },\n"
                 "      text: function () { return Promise.resolve(JSON.stringify(hit)); } });\n"
                 "  };\n}());</script>")
    parts.append("<script>" + guard(support) + "</script>")

    # The head, minus the wrapper and the two script tags now inlined above.
    head = html.split("<head>", 1)[1].split("</head>", 1)[0]
    head = head.replace('<script src="./support.js"></script>', "")
    head = re.sub(r'<link rel="canonical"[^>]*>', "", head)
    body = html.split("<body>", 1)[1].rsplit("</body>", 1)[0]
    # The design system, inlined the same way. Its stylesheet is nothing but @imports of
    # the token files, and an @import is another request the page cannot make, so they are
    # folded in where they are named.
    def inline_css(path):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r'@import\s+url\(["\']?([^"\')]+)["\']?\);',
                      lambda m: inline_css(path.parent / m.group(1)), text)
        # And the faces the tokens name, since a font is another request the page cannot
        # make, and the site in a fallback face is not the site.
        return re.sub(r'url\(["\']?([^"\')]+\.woff2?)["\']?\)',
                      lambda m: font(path.parent / m.group(1)), text)

    def font(path):
        if not path.exists():
            return 'url("' + path.name + '")'
        kind = "font/woff2" if path.suffix == ".woff2" else "font/woff"
        return ('url("data:' + kind + ";base64,"
                + base64.b64encode(path.read_bytes()).decode() + '")')

    css = inline_css(ROOT / "ds" / "styles.css")
    ds = (ROOT / "ds" / "_ds_bundle.js").read_text(encoding="utf-8")
    # Those two tags sit inside <helmet>, which sits inside <x-dc> — and everything inside
    # <x-dc> is the template. Inlined where they stand, the bundle would be twenty
    # kilobytes of JavaScript handed to the template parser as markup. They go to the head
    # instead, which is where the helmet was going to hoist them to anyway.
    body = body.replace('<link rel="stylesheet" href="ds/styles.css">', "")
    body = body.replace('<script src="ds/_ds_bundle.js"></script>', "")
    parts.insert(0, "<style>" + css + "</style>")
    parts.insert(1, "<script>" + guard(ds) + "</script>")

    out = Path(args.out)
    out.write_text(head + "\n".join(parts) + body, encoding="utf-8")
    print(f"wrote {out}  {out.stat().st_size / 1024 / 1024:.1f} MB  "
          f"({', '.join(libs)})")


if __name__ == "__main__":
    main()
