"""Generate the (original, neutral) brand assets for this integration.

The icon is a stylised fuel pump with a drop in blue/green tones. It is an
original design and deliberately does not resemble any TotalEnergies logo,
colours or marks. Run: python scripts/make_brand.py  (needs cairosvg + Pillow)
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "custom_components" / "totalenergies_stations" / "brand"
DOCS = ROOT / "docs"

BLUE = "#1f5f8b"
BLUE_LIGHT = "#2e86c1"
GREEN = "#27ae60"
WHITE = "#ffffff"


def icon_svg(fg: str = BLUE, accent: str = GREEN, bg: str | None = None) -> str:
    """Return the icon SVG (256x256 viewBox, transparent background)."""
    background = f'<rect x="0" y="0" width="256" height="256" rx="48" fill="{bg}"/>' if bg else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
{background}
<!-- pump body -->
<rect x="56" y="44" width="104" height="168" rx="16" fill="{fg}"/>
<rect x="72" y="60" width="72" height="48" rx="8" fill="{WHITE}"/>
<!-- base plate -->
<rect x="44" y="204" width="128" height="18" rx="6" fill="{fg}"/>
<!-- hose + nozzle -->
<path d="M160 92 h22 a16 16 0 0 1 16 16 v70 a10 10 0 0 0 20 0 v-60" fill="none" stroke="{fg}" stroke-width="14" stroke-linecap="round"/>
<rect x="206" y="92" width="24" height="30" rx="6" fill="{fg}"/>
<!-- drop (accent) -->
<path d="M108 126 c-18 24 -26 36 -26 50 a26 26 0 0 0 52 0 c0 -14 -8 -26 -26 -50z" fill="{accent}"/>
<circle cx="99" cy="176" r="5" fill="{WHITE}" opacity="0.8"/>
</svg>"""


def logo_svg(fg: str, text_color: str) -> str:
    """Return the logo SVG: icon + neutral wordmark (no trademarks)."""
    icon = icon_svg(fg=fg).split("\n", 1)[1].rsplit("</svg>", 1)[0]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 256" width="900" height="256">
<g transform="translate(0,0)">{icon}</g>
<text x="280" y="128" font-family="DejaVu Sans, Arial, Helvetica, sans-serif" font-size="78" font-weight="bold" fill="{text_color}">Stations</text>
<text x="280" y="210" font-family="DejaVu Sans, Arial, Helvetica, sans-serif" font-size="64" fill="{fg}">carburant</text>
</svg>"""


def render(svg: str, width: int, out: Path) -> None:
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=width)
    img = Image.open(BytesIO(png)).convert("RGBA")
    img.save(out, optimize=True)
    print(f"{out.relative_to(ROOT)}: {img.size[0]}x{img.size[1]} {out.stat().st_size} bytes")


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    render(icon_svg(), 256, BRAND / "icon.png")
    render(icon_svg(), 512, BRAND / "icon@2x.png")
    render(icon_svg(fg=BLUE_LIGHT), 256, BRAND / "dark_icon.png")
    render(icon_svg(fg=BLUE_LIGHT), 512, BRAND / "dark_icon@2x.png")
    render(logo_svg(BLUE, "#1b2631"), 900, BRAND / "logo.png")
    render(logo_svg(BLUE, "#1b2631"), 1800, BRAND / "logo@2x.png")
    render(logo_svg(BLUE_LIGHT, WHITE), 900, BRAND / "dark_logo.png")
    render(logo_svg(BLUE_LIGHT, WHITE), 1800, BRAND / "dark_logo@2x.png")
    render(icon_svg(), 128, DOCS / "icon.png")
    (DOCS / "icon.svg").write_text(icon_svg(), encoding="utf-8")


if __name__ == "__main__":
    main()
