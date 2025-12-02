#!/usr/bin/env python3
"""Generate favicon files from SVG source.

This script generates all required favicon formats for cross-browser compatibility.
Run once after creating or updating the SVG favicon.

Usage:
    pip install cairosvg Pillow
    python scripts/generate_favicons.py
"""

import io
from pathlib import Path

try:
    import cairosvg
    from PIL import Image
except ImportError:
    print("Required dependencies not found. Install them with:")
    print("  pip install cairosvg Pillow")
    raise SystemExit(1)


def svg_to_png(svg_path: Path, output_path: Path, size: int) -> None:
    """Convert SVG to PNG at specified size."""
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(output_path),
        output_width=size,
        output_height=size,
    )
    print(f"  Created: {output_path.name} ({size}x{size})")


def create_ico(png_paths: list[Path], output_path: Path) -> None:
    """Create ICO file from PNG images."""
    images = [Image.open(p) for p in png_paths]
    # ICO format: save the largest image and include smaller as additional sizes
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:],
    )
    print(f"  Created: {output_path.name}")


def main() -> None:
    """Generate all favicon formats from SVG source."""
    # Paths
    project_root = Path(__file__).parent.parent
    static_dir = project_root / "static"
    svg_path = static_dir / "favicon.svg"

    if not svg_path.exists():
        print(f"Error: SVG source not found at {svg_path}")
        raise SystemExit(1)

    print(f"Generating favicons from: {svg_path}")
    print()

    # Generate PNG files at various sizes
    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "android-chrome-192x192.png": 192,
        "android-chrome-512x512.png": 512,
    }

    print("PNG files:")
    for filename, size in sizes.items():
        svg_to_png(svg_path, static_dir / filename, size)

    # Generate ICO file (contains 16x16, 32x32, and 48x48)
    print()
    print("ICO file:")

    # Create 48x48 temporarily for ICO
    ico_sizes = [16, 32, 48]
    ico_pngs = []

    for size in ico_sizes:
        temp_path = static_dir / f"temp-{size}.png"
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(temp_path),
            output_width=size,
            output_height=size,
        )
        ico_pngs.append(temp_path)

    create_ico(ico_pngs, static_dir / "favicon.ico")

    # Clean up temp files
    for temp_path in ico_pngs:
        temp_path.unlink()

    print()
    print("Done! All favicon files generated successfully.")


if __name__ == "__main__":
    main()
