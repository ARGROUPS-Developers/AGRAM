"""AGRAM icon banata hai (agar assets/icon.png pehle se na ho)."""
import os
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join("assets", "icon.png")
if os.path.exists(OUT):
    print("icon.png maujood hai, naya nahi banaya")
    raise SystemExit(0)

S, K = 1024, 2
W = S * K
BG, BODY, CYAN, PURPLE = (11, 11, 18), (27, 34, 48), (94, 214, 232), (170, 90, 240)

def pts(lst):
    return [(x * K, y * K) for x, y in lst]

img = Image.new("RGB", (W, W), BG)

# purple glow right edge
glow = Image.new("RGB", (W, W), (0, 0, 0))
ImageDraw.Draw(glow).line(pts([(572, 112), (958, 908)]), fill=PURPLE, width=34 * K)
glow = glow.filter(ImageFilter.GaussianBlur(26 * K))
img = Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.7)

d = ImageDraw.Draw(img)
outer = [(468, 112), (572, 112), (958, 908), (752, 908), (722, 806),
         (432, 806), (272, 908), (66, 908)]
d.polygon(pts(outer), fill=BODY)
# counter (triangle hole) and slit
d.polygon(pts([(528, 692), (578, 566), (664, 692)]), fill=BG)
d.polygon(pts([(556, 236), (524, 420), (540, 450), (580, 330)]), fill=BG)
# neon edges
d.line(pts([(468, 112), (66, 908)]), fill=CYAN, width=7 * K)
d.line(pts([(468, 112), (572, 112)]), fill=(150, 170, 190), width=6 * K)
d.line(pts([(572, 112), (958, 908)]), fill=PURPLE, width=8 * K)
d.line(pts([(528, 692), (578, 566), (664, 692), (528, 692)]), fill=CYAN, width=5 * K)

img = img.resize((S, S), Image.LANCZOS)
os.makedirs("assets", exist_ok=True)
img.save(OUT)
print("icon.png bana diya")

