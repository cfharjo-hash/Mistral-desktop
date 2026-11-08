import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOP = (255, 206, 0)
BOTTOM = (255, 90, 0)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (1, size))
    for y in range(size):
        t = y / max(1, size - 1)
        grad.putpixel((0, y), (
            int(TOP[0] + (BOTTOM[0] - TOP[0]) * t),
            int(TOP[1] + (BOTTOM[1] - TOP[1]) * t),
            int(TOP[2] + (BOTTOM[2] - TOP[2]) * t),
            255,
        ))
    grad = grad.resize((size, size))
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    margin = size // 16
    md.rounded_rectangle([margin, margin, size - margin, size - margin],
                         radius=size // 5, fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = margin, margin, size - margin, size - margin
    w, h = x1 - x0, y1 - y0
    a, b = x0 + w * 0.24, y0 + h * 0.26
    c, e = x1 - w * 0.24, y1 - h * 0.26
    midx = (a + c) / 2
    midy = y0 + h * 0.62
    lw = max(2, int(w * 0.13))
    d.line([(a, e), (a, b), (midx, midy), (c, b), (c, e)],
           fill=(255, 255, 255, 255), width=lw, joint="curve")
    return img


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "mistral_desktop" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    icon = draw_icon(512)
    icon.save(out_dir / "icon.png")
    icon.save(out_dir / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                                           (64, 64), (128, 128), (256, 256)])
    print(f"wrote {out_dir / 'icon.png'} and {out_dir / 'icon.ico'}")


if __name__ == "__main__":
    sys.exit(main())
