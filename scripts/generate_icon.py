"""Generate a macOS .icns app icon for Reading Assistant."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "build" / "AppIcon.iconset"


def draw_book(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = size // 10
    body = size - 2 * pad
    r = size // 28
    color = (29, 29, 31)

    # Book body (rounded rect via antialiased ellipse corners - approximate with rect)
    bx, by = pad, int(size * 0.22)
    bw, bh = body, int(size * 0.6)

    draw.rounded_rectangle(
        [bx, by, bx + bw, by + bh],
        radius=r,
        fill=color,
    )

    # Spine line
    spine_x = bx + bw // 5
    draw.line(
        [spine_x, by + r, spine_x, by + bh - r],
        fill=(255, 255, 255),
        width=max(1, size // 60),
    )

    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    sizes = [
        (16, "icon_16x16"),
        (32, "icon_16x16@2x"),
        (32, "icon_32x32"),
        (64, "icon_32x32@2x"),
        (128, "icon_128x128"),
        (256, "icon_128x128@2x"),
        (256, "icon_256x256"),
        (512, "icon_256x256@2x"),
        (512, "icon_512x512"),
        (1024, "icon_512x512@2x"),
    ]

    for px, name in sizes:
        img = draw_book(px)
        path = OUT / f"{name}.png"
        img.save(path)
        print(f"  {path.name}  {px}x{px}")

    icns_path = OUT.parent / "AppIcon.icns"
    subprocess.run(
        ["iconutil", "--convert", "icns", str(OUT), "--output", str(icns_path)],
        check=True,
    )
    print(f"\nCreated {icns_path}")


if __name__ == "__main__":
    main()
