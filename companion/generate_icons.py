#!/usr/bin/env python3
"""
Generate placeholder app icons for the companion app.

Creates icon.png, icon.ico, and icon.icns from a generated image.
Requires Pillow (pip install Pillow).

Usage:
    python generate_icons.py
"""

import struct
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def create_icon_image(size: int = 256) -> "Image.Image":
    """Create a simple app icon image."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle - dark blue
    padding = size // 16
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=(30, 58, 95, 255),
        outline=(80, 140, 200, 255),
        width=max(1, size // 32),
    )

    # Draw "EBO" text
    text = "EBO"
    # Use default font, scaled roughly
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size // 4)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = (size - text_h) // 2
    draw.text((x, y), text, fill=(200, 220, 255, 255), font=font)

    return img


def create_ico(img: "Image.Image", path: Path) -> None:
    """Save as .ico with multiple sizes."""
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(str(path), format="ICO", sizes=sizes)


def create_icns_from_png(png_path: Path, icns_path: Path) -> None:
    """Create a minimal .icns file from a PNG."""
    # Read the PNG data
    png_data = png_path.read_bytes()

    # .icns format: 4-byte magic, 4-byte total size, then icon entries
    # Use 'ic07' type (128x128 PNG) as a simple single-entry icns
    icon_type = b"ic07"  # 128x128 PNG
    entry_size = 8 + len(png_data)  # type(4) + size(4) + data

    total_size = 8 + entry_size  # header(8) + entry

    with open(icns_path, "wb") as f:
        f.write(b"icns")
        f.write(struct.pack(">I", total_size))
        f.write(icon_type)
        f.write(struct.pack(">I", entry_size))
        f.write(png_data)


def main() -> None:
    out_dir = Path(__file__).parent

    if not HAS_PIL:
        print("Pillow not installed. Creating minimal placeholder icons.")
        # Create a minimal 1x1 PNG as fallback
        # PNG header + minimal IHDR + IDAT + IEND
        minimal_png = (
            b"\x89PNG\r\n\x1a\n"  # PNG signature
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
            b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
            b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        (out_dir / "icon.png").write_bytes(minimal_png)
        print(f"  Created {out_dir / 'icon.png'} (minimal placeholder)")
        print("\nInstall Pillow for proper icons: pip install Pillow")
        return

    print("Generating companion app icons...")

    # Generate base image
    img = create_icon_image(256)

    # Save PNG (128x128 for icns compatibility)
    png_path = out_dir / "icon.png"
    img_128 = img.resize((128, 128), Image.LANCZOS)
    img_128.save(str(png_path), format="PNG")
    print(f"  Created {png_path}")

    # Save ICO (Windows)
    ico_path = out_dir / "icon.ico"
    create_ico(img, ico_path)
    print(f"  Created {ico_path}")

    # Save ICNS (macOS)
    icns_path = out_dir / "icon.icns"
    create_icns_from_png(png_path, icns_path)
    print(f"  Created {icns_path}")

    print("\nDone! Icons ready for PyInstaller build.")


if __name__ == "__main__":
    main()
