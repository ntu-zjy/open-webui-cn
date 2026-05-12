"""Generate brand logo assets: a circular gradient with the brand character.

Outputs (all under static/static/):
  favicon.png        32x32
  favicon-96x96.png  96x96
  favicon-dark.png   32x32 dark mode
  apple-touch-icon.png 180x180
  logo.png           512x512
  splash.png         512x512 (with brand text)
  splash-dark.png    512x512 dark
  favicon.svg        scalable
  favicon.ico        16+32+48 multi-resolution

Re-runnable. Tuned for the brand "思源" — change CHARACTER + NAME below.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CHARACTER = '思'
NAME = '思源'
FONT_PATH = '/System/Library/Fonts/STHeiti Medium.ttc'

# Indigo-600 → Violet-600 (modern AI brand palette)
GRAD_START = (79, 70, 229)
GRAD_END = (147, 51, 234)
GRAD_START_DARK = (49, 46, 129)
GRAD_END_DARK = (88, 28, 135)

STATIC = Path(__file__).resolve().parent.parent / 'static' / 'static'


def _gradient_circle(size: int, start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    pixels = img.load()
    # Diagonal linear gradient
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            r = int(start[0] + (end[0] - start[0]) * t)
            g = int(start[1] + (end[1] - start[1]) * t)
            b = int(start[2] + (end[2] - start[2]) * t)
            pixels[x, y] = (r, g, b, 255)
    # Mask to circle
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def _draw_character(base: Image.Image, char: str, *, color=(255, 255, 255, 255), ratio: float = 0.62) -> Image.Image:
    size = base.size[0]
    font_size = int(size * ratio)
    font = ImageFont.truetype(FONT_PATH, font_size)
    draw = ImageDraw.Draw(base)
    bbox = draw.textbbox((0, 0), char, font=font, anchor='lt')
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (size - w) // 2 - bbox[0]
    y = (size - h) // 2 - bbox[1]
    draw.text((x, y), char, font=font, fill=color)
    return base


def make_icon(size: int, *, dark: bool = False) -> Image.Image:
    start = GRAD_START_DARK if dark else GRAD_START
    end = GRAD_END_DARK if dark else GRAD_END
    img = _gradient_circle(size, start, end)
    return _draw_character(img, CHARACTER, ratio=0.62)


def make_splash(size: int = 512, *, dark: bool = False) -> Image.Image:
    canvas = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    icon_size = int(size * 0.6)
    icon = make_icon(icon_size, dark=dark)
    canvas.paste(icon, ((size - icon_size) // 2, int(size * 0.18)), icon)
    font = ImageFont.truetype(FONT_PATH, int(size * 0.12))
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), NAME, font=font, anchor='lt')
    w = bbox[2] - bbox[0]
    text_color = (255, 255, 255, 255) if dark else (30, 27, 75, 255)
    draw.text(((size - w) // 2 - bbox[0], int(size * 0.78)), NAME, font=font, fill=text_color)
    return canvas


def main() -> None:
    STATIC.mkdir(parents=True, exist_ok=True)

    make_icon(32).save(STATIC / 'favicon.png')
    make_icon(96).save(STATIC / 'favicon-96x96.png')
    make_icon(32, dark=True).save(STATIC / 'favicon-dark.png')
    make_icon(180).save(STATIC / 'apple-touch-icon.png')
    make_icon(512).save(STATIC / 'logo.png')
    make_splash(512).save(STATIC / 'splash.png')
    make_splash(512, dark=True).save(STATIC / 'splash-dark.png')

    ico = make_icon(48)
    ico.save(STATIC / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#4F46E5"/>
      <stop offset="100%" stop-color="#9333EA"/>
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="50" fill="url(#g)"/>
  <text x="50" y="50" text-anchor="middle" dominant-baseline="central"
        font-family="STHeiti, 'PingFang SC', 'Microsoft YaHei', sans-serif"
        font-size="62" font-weight="600" fill="#ffffff">{CHARACTER}</text>
</svg>'''
    (STATIC / 'favicon.svg').write_text(svg, encoding='utf-8')

    for p in sorted(STATIC.glob('favicon*')) + sorted(STATIC.glob('logo*')) + sorted(STATIC.glob('splash*')) + sorted(STATIC.glob('apple-touch-icon*')):
        print(f'  {p.relative_to(STATIC.parent.parent)}')


if __name__ == '__main__':
    main()
