"""Draw the feed's cover art (3000×3000 PNG, what Apple Podcasts asks for) in the app's style.

Run once from backend/:  uv run --with pillow python scripts/make_cover.py
The result, app/static/cover.png, is versioned.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 3000
BACKGROUND, INK, ON_AIR, AMBER = "#0f141b", "#f5f1ea", "#f0623e", "#e8b04a"
FONTS = Path(__file__).parents[2] / "frontend/node_modules/@fontsource/instrument-serif/files"
OUT = Path(__file__).parents[1] / "app/static/cover.png"

img = Image.new("RGB", (SIZE, SIZE), BACKGROUND)
draw = ImageDraw.Draw(img)

# The ON AIR light, top left.
draw.ellipse((260, 260, 460, 460), fill=ON_AIR)

# A waveform across the middle: bars whose height follows two slow sines.
bars, gap = 48, 18
width = (SIZE - 2 * 260 - (bars - 1) * gap) / bars
for i in range(bars):
    h = 120 + 520 * abs(math.sin(i / 4.5) * math.cos(i / 11))
    x = 260 + i * (width + gap)
    color = ON_AIR if 18 <= i <= 26 else AMBER if i % 7 == 0 else "#2a3340"
    draw.rounded_rectangle((x, 1500 - h, x + width, 1500 + h), radius=width / 2, fill=color)

serif = ImageFont.truetype(str(FONTS / "instrument-serif-latin-400-normal.woff"), 380)
italic = ImageFont.truetype(str(FONTS / "instrument-serif-latin-400-italic.woff"), 380)
draw.text((260, 2080), "Personal", font=serif, fill=INK)
draw.text((260, 2440), "Podcast", font=italic, fill=ON_AIR)

OUT.parent.mkdir(exist_ok=True)
img.save(OUT, optimize=True)
print(OUT, OUT.stat().st_size // 1024, "KB")
