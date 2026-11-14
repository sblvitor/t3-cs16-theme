#!/usr/bin/env python3
"""Build dist/theme.json from sprites/*.txt, src/theme.css and src/theme.base.json.

Usage: python3 build.py
Outputs:
  dist/theme.json   the T3 Code theme (colors + CSS with sprites embedded)
  dist/sheet.png    8x preview of every sprite
"""
import base64, io, json, pathlib, re
from PIL import Image

ROOT = pathlib.Path(__file__).parent
PALETTE = {k: v for k, v in json.loads((ROOT / "sprites/palette.json").read_text()).items() if not k.startswith("_")}
CSS_LIMIT = 20000

# HUD strings, rendered with the 5x7 font below. Keys become @name@ in src/theme.css.
HUD = {"hudl": "+ 100  S 100", "hudr": "30 | 90"}
FONT = {
    "0": ["AAAAA", "AA.AA", "AA.AA", "AA.AA", "AA.AA", "AA.AA", "AAAAA"],
    "1": ["..AA.", ".AAA.", "..AA.", "..AA.", "..AA.", "..AA.", ".AAAA"],
    "3": ["AAAAA", "...AA", "...AA", ".AAAA", "...AA", "...AA", "AAAAA"],
    "9": ["AAAAA", "AA.AA", "AA.AA", "AAAAA", "...AA", "...AA", "AAAAA"],
    "+": [".AAA.", ".AAA.", "AAAAA", "AAAAA", "AAAAA", ".AAA.", ".AAA."],  # health cross
    "S": ["AAAAA", "AAAAA", "AAAAA", "AAAAA", ".AAA.", ".AAA.", "..A.."],  # armor shield
    "|": ["..A..", "..A..", "..A..", "..A..", "..A..", "..A..", "..A.."],
    "$": ["..A..", ".AAAA", "AA.A.", ".AAA.", ".A.AA", "AAAA.", "..A.."],
    " ": ["...", "...", "...", "...", "...", "...", "..."],
}


def hud_rows(text):
    rows = [""] * 7
    for ch in text:
        for i in range(7):
            rows[i] += FONT[ch][i] + "."
    return rows


def render(rows):
    rows = [r for r in rows if r.strip()]
    im = Image.new("RGBA", (max(map(len, rows)), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                c = PALETTE[ch]
                im.putpixel((x, y), tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (255,))
    return im


def to_b64(im):
    buf = io.BytesIO()
    colors = len(set(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()))
    im.quantize(colors=min(256, colors), method=Image.Quantize.FASTOCTREE).save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    sprites = {p.stem: render(p.read_text().splitlines()) for p in sorted((ROOT / "sprites").glob("*.txt"))}
    sprites.update({k: render(hud_rows(v)) for k, v in HUD.items()})

    css = (ROOT / "src/theme.css").read_text()
    for name, im in sprites.items():
        css = css.replace(f"@{name}@", to_b64(im))
    missing = set(re.findall(r"@(\w+)@", css))
    assert not missing, f"no sprite for placeholders: {missing}"
    assert len(css) <= CSS_LIMIT, f"css is {len(css)} chars, limit {CSS_LIMIT}"

    theme = json.loads((ROOT / "src/theme.base.json").read_text())
    theme["css"] = css
    (ROOT / "dist").mkdir(exist_ok=True)
    (ROOT / "dist/theme.json").write_text(json.dumps(theme, indent=2) + "\n")

    scaled = [im.resize((im.width * 8, im.height * 8), Image.NEAREST) for im in sprites.values()]
    sheet = Image.new("RGB", (sum(i.width + 24 for i in scaled) + 24, max(i.height for i in scaled) + 48), "#1f2133")
    x = 24
    for im in scaled:
        sheet.paste(im, (x, 24), im)
        x += im.width + 24
    sheet.save(ROOT / "dist/sheet.png")
    print(f"dist/theme.json: {len(css)}/{CSS_LIMIT} css chars, {len(sprites)} sprites")


if __name__ == "__main__":
    main()
