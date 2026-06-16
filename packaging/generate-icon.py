from pathlib import Path

from collections import deque

from PIL import Image, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "icons" / "icon.png"
RAW_SOURCE = ROOT / "assets" / "icons" / "icon-source.png"
APP_ICO = ROOT / "assets" / "icons" / "arcadia.ico"
FRONTEND_ICO = ROOT / "frontend" / "favicon.ico"
FRONTEND_PNG = ROOT / "frontend" / "assets" / "arcadia-icon.png"


def build_icon() -> Image.Image:
    size = 1024
    source_path = RAW_SOURCE if RAW_SOURCE.exists() else SOURCE
    source = Image.open(source_path).convert("RGBA")
    source = remove_connected_light_background(source)
    source = enhance_mark(source)

    bbox = source.getbbox()
    logo = source.crop(bbox) if bbox else source
    logo.thumbnail((820, 820), Image.Resampling.LANCZOS)

    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    return icon


def remove_connected_light_background(image: Image.Image) -> Image.Image:
    """Remove only the outer light background, preserving internal white details."""
    width, height = image.size
    pixels = image.load()
    visited = set()
    queue = deque()

    def is_background(x: int, y: int) -> bool:
        r, g, b, a = pixels[x, y]
        if a == 0:
            return True
        return min(r, g, b) >= 218 and max(r, g, b) - min(r, g, b) <= 30

    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in visited or not (0 <= x < width and 0 <= y < height):
            continue
        visited.add((x, y))
        if not is_background(x, y):
            continue
        pixels[x, y] = (255, 255, 255, 0)
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    return image


def enhance_mark(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    rgb = image.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.14)
    rgb = ImageEnhance.Color(rgb).enhance(1.08)
    enhanced = rgb.convert("RGBA")
    enhanced.putalpha(alpha)
    return enhanced


def main() -> None:
    icon = build_icon()
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    APP_ICO.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_PNG.parent.mkdir(parents=True, exist_ok=True)
    icon.save(SOURCE)
    icon.save(APP_ICO, format="ICO", sizes=sizes)
    icon.save(FRONTEND_ICO, format="ICO", sizes=sizes)
    icon.save(FRONTEND_PNG)
    print(f"Wrote {APP_ICO}")


if __name__ == "__main__":
    main()
