"""Fetch 8 cartoon default avatars from DiceBear (notionists style).

Outputs to static/static/avatars/{1..8}.svg. Re-runnable.

Why DiceBear: free CC0-licensed cartoon avatar library with many styles.
Notionists = Notion-inspired cute stick figures, brand-neutral.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

SEEDS = ['Maple', 'Felix', 'Aneka', 'Sam', 'Oliver', 'Mia', 'Luna', 'Kai']
STYLE = 'notionists'
BG_COLORS = 'ffd5dc,ffdfbf,c0aede,b6e3f4,d1d4f9,c4e8c2'

OUT = Path(__file__).resolve().parent.parent / 'static' / 'static' / 'avatars'


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for i, seed in enumerate(SEEDS, 1):
        url = (
            f'https://api.dicebear.com/9.x/{STYLE}/svg'
            f'?seed={seed}&backgroundColor={BG_COLORS}&backgroundType=solid'
        )
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read()
        (OUT / f'{i}.svg').write_bytes(data)
        print(f'  static/static/avatars/{i}.svg  ({seed}, {len(data)} bytes)')


if __name__ == '__main__':
    main()
