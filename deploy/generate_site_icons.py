"""
Generate site / PWA icons from assets/mte_logo.png.

Outputs:
  frontend/public/favicon.ico
  frontend/public/favicon-32x32.png
  frontend/public/apple-touch-icon.png
  pwa/icons/icon-192x192.png
  pwa/icons/icon-512x512.png

Requires: Pillow (pip install pillow)
Usage (from project root):
  python deploy/generate_site_icons.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_LOGO = PROJECT_ROOT / "assets" / "mte_logo.png"
# Light canvas so the red/black MTE seal reads in browser chrome and on home screens.
BACKGROUND = (245, 245, 245, 255)


def make_icon(source: Image.Image, size: int, pad_ratio: float) -> Image.Image:
    """
    Place the full MTE logo centered on a light square canvas.

    Args:
        source: RGBA source logo.
        size: Output width/height in pixels.
        pad_ratio: Fraction of size reserved as padding on each side.

    Returns:
        Square RGBA icon image.
    """
    canvas = Image.new("RGBA", (size, size), BACKGROUND)
    pad = max(1, int(size * pad_ratio))
    inner = size - (2 * pad)
    logo = source.copy()
    logo.thumbnail((inner, inner), Image.Resampling.LANCZOS)
    x = (size - logo.width) // 2
    y = (size - logo.height) // 2
    canvas.paste(logo, (x, y), logo)
    return canvas


def main() -> None:
    """Write favicon, apple-touch, and PWA icon files."""
    if not SOURCE_LOGO.is_file():
        raise FileNotFoundError(f"Missing logo: {SOURCE_LOGO}")

    source = Image.open(SOURCE_LOGO).convert("RGBA")
    public_dir = PROJECT_ROOT / "frontend" / "public"
    pwa_dir = PROJECT_ROOT / "pwa" / "icons"
    public_dir.mkdir(parents=True, exist_ok=True)
    pwa_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[tuple[Path, int, float]] = [
        (public_dir / "favicon-32x32.png", 32, 0.10),
        (public_dir / "apple-touch-icon.png", 180, 0.06),
        (pwa_dir / "icon-192x192.png", 192, 0.06),
        (pwa_dir / "icon-512x512.png", 512, 0.06),
    ]
    for path, size, pad in outputs:
        make_icon(source, size, pad).save(path, format="PNG", optimize=True)
        print(f"Wrote {path}")

    ico_sizes = [16, 32, 48]
    ico_images = [make_icon(source, size, 0.10 if size <= 32 else 0.06) for size in ico_sizes]
    ico_path = public_dir / "favicon.ico"
    ico_images[0].save(
        ico_path,
        format="ICO",
        sizes=[(size, size) for size in ico_sizes],
        append_images=ico_images[1:],
    )
    print(f"Wrote {ico_path}")


if __name__ == "__main__":
    main()
