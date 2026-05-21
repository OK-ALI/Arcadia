from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "icons" / "icon.png"
APP_ICO = ROOT / "assets" / "icons" / "arcadia.ico"
FRONTEND_ICO = ROOT / "frontend" / "favicon.ico"
FRONTEND_PNG = ROOT / "frontend" / "assets" / "arcadia-icon.png"


def build_icon() -> Image.Image:
    source = Image.open(SOURCE).convert("RGBA")
    size = 1024
    background = Image.new("RGBA", (size, size), (255, 82, 31, 255))
    pixels = background.load()

    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            pixels[x, y] = (
                int(255 * (1 - t) + 194 * t),
                int(92 * (1 - t) + 18 * t),
                int(31 * (1 - t) + 12 * t),
                255,
            )

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    draw.ellipse((180, 650, 860, 910), fill=(70, 0, 0, 92))
    background.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(34)))

    bbox = source.getbbox()
    logo = source.crop(bbox) if bbox else source
    logo.thumbnail((760, 760), Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    layer.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2 - 18))
    background.alpha_composite(layer)
    return background


def main() -> None:
    icon = build_icon()
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    APP_ICO.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_PNG.parent.mkdir(parents=True, exist_ok=True)
    icon.save(APP_ICO, format="ICO", sizes=sizes)
    icon.save(FRONTEND_ICO, format="ICO", sizes=sizes)
    icon.save(FRONTEND_PNG)
    print(f"Wrote {APP_ICO}")


if __name__ == "__main__":
    main()
