from functools import lru_cache

from PIL import Image, ImageDraw

COLORS = {"off": (128, 128, 128), "on": (34, 170, 85), "paused": (230, 160, 20)}
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


@lru_cache(maxsize=None)
def make_icon(state: str, size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = size // 16
    d.ellipse((pad, pad, size - 1 - pad, size - 1 - pad), fill=COLORS[state] + (255,),
              outline=(0, 0, 0, 90), width=max(1, size // 32))
    w = max(2, size // 10)
    c, r = size / 2, size * 0.26
    d.arc((c - r, c - r, c + r, c + r), start=-60, end=240, fill="white", width=w)
    d.line((c, c - r - w / 2, c, c), fill="white", width=w)
    return img


def save_ico(path) -> None:
    make_icon("on", 256).save(path, sizes=ICO_SIZES)
