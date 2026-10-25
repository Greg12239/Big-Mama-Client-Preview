#!/usr/bin/env python3
"""Deterministically normalize Big Mama menu imagery into 1600x1200 WebP files.

Source assets are read only. Crop rectangles are approved composition windows,
not automatic foreground crops; they intentionally retain product shadows,
packaging, brush strokes, and safe breathing room.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "public" / "assets" / "menu" / "normalized"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
CANVAS_SIZE = (1600, 1200)
SAFE_AREA = (160, 120, 1440, 1020)
WEBP_OPTIONS = {"format": "WEBP", "quality": 95, "method": 6}


# crop=(left, top, right, bottom); placement=(x, y, width, height)
# These rectangles preserve each complete photographed composition. The Soft Drink
# crop intentionally excludes only the user-approved top rule and close icon.
ASSETS: list[dict[str, Any]] = [
    {"id": "classic-cheese-burger", "source": "classic cheese burger.png", "output": "classic-cheese-burger.webp", "crop": (250, 140, 1550, 800), "placement": (180, 285, 1240, 630)},
    {"id": "bacon-lovers-double", "source": "bacon-lovers-double.png", "output": "bacon-lovers-double.webp", "crop": (70, 58, 1384, 894), "placement": (210, 224, 1180, 751)},
    {"id": "truffle-oh-mama-double", "source": "truffle-oh-mama-double.png", "output": "truffle-oh-mama-double.webp", "crop": (60, 75, 1234, 945), "placement": (240, 186, 1120, 829)},
    {"id": "mamas-original-single", "source": "mamas-original-single.png", "output": "mamas-original-single.webp", "crop": (66, 84, 1285, 905), "placement": (240, 223, 1120, 754), "manual_review": "Connected neutral empty background is removed manually; food, packaging, and shadow pixels are retained."},
    {"id": "mama-in-paris", "source": "Mama in Paris.png", "output": "mama-in-paris.webp", "crop": (120, 155, 1578, 790), "placement": (180, 330, 1240, 540)},
    {"id": "big-tokyo", "source": "big-tokyo.png", "output": "big-tokyo.webp", "crop": (0, 330, 1123, 1401), "placement": (360, 150, 881, 840), "manual_review": "Full source width retained because composition reaches both edges."},
    {"id": "crispy-mam", "source": "CRISPY MAM.png", "output": "crispy-mam.webp", "crop": (220, 80, 1426, 870), "placement": (230, 226, 1140, 747)},
    {"id": "lava-mam-chicken", "source": "lava-mam-chicken.png", "output": "lava-mam-chicken.webp", "crop": (180, 62, 1480, 950), "placement": (220, 204, 1160, 793), "manual_review": "Source bottom edge retained."},
    {"id": "truffle-parmesan-chicken", "source": "truffle-parmesan-chicken.png", "output": "truffle-parmesan-chicken.webp", "crop": (200, 80, 1470, 870), "placement": (220, 240, 1160, 721)},
    {"id": "crispy-chicken-strips", "source": "APPETIZER 1.png", "output": "crispy-chicken-strips.webp", "crop": (240, 140, 1530, 808), "placement": (200, 290, 1200, 621)},
    {"id": "big-mama-fries", "source": "big-mama-fries.jpg", "output": "big-mama-fries.webp", "crop": (300, 55, 990, 940), "placement": (470, 142, 660, 846)},
    {"id": "truffle-parmesan-fries", "source": "truffle parmesan fries.png", "output": "truffle-parmesan-fries.webp", "crop": (230, 225, 1565, 740), "placement": (180, 350, 1240, 478)},
    {"id": "kids-meal", "source": "KIDS MEAL.png", "output": "kids-meal.webp", "crop": (100, 140, 1448, 945), "placement": (200, 240, 1200, 717), "manual_review": "Source right edge retained."},
    {"id": "big-mayo-sauce", "source": "Big mayo sauce.png", "output": "big-mayo-sauce.webp", "crop": (70, 130, 1340, 1035), "placement": (225, 190, 1151, 820), "group": "sauces"},
    {"id": "truffle-mayo-sauce", "source": "Truffle mayo sauce.png", "output": "truffle-mayo-sauce.webp", "crop": (75, 110, 1360, 1015), "placement": (222, 193, 1157, 815), "group": "sauces"},
    {"id": "dragon-sauce", "source": "Dragon sauce.png", "output": "dragon-sauce.webp", "crop": (65, 130, 1340, 1035), "placement": (223, 190, 1155, 820), "group": "sauces"},
    {"id": "red-dragon-sauce", "source": "RED DRAGON SAUCE.png", "output": "red-dragon-sauce.webp", "crop": (50, 75, 1380, 1040), "placement": (235, 190, 1131, 820), "group": "sauces"},
    {"id": "original-double-choco-cookie", "source": "original-double-choco-cookie.jpg", "output": "original-double-choco-cookie.webp", "crop": (50, 30, 1250, 905), "placement": (250, 199, 1100, 802)},
    {"id": "soft-drink", "source": "Soft drink.png", "output": "soft-drink.webp", "crop": (260, 40, 430, 370), "placement": (604, 220, 391, 759), "manual_review": "Approved removal of only the top rule and close icon; drink pixels remain untouched. The 2.3x source crop resize preserves the current rendered can scale."},
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def foreground_bounds(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Conservative bounds for audit reporting, not crop selection."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    alpha_min, _ = alpha.getextrema()
    if alpha_min < 250:
        return alpha.point(lambda value: 255 if value >= 8 else 0).getbbox()

    rgb = rgba.convert("RGB")
    width, height = rgb.size
    edge_points = (
        (0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1),
        (width // 2, 0), (width // 2, height - 1), (0, height // 2), (width - 1, height // 2),
    )
    samples = [rgb.getpixel(point) for point in edge_points]
    background = tuple(sorted(pixel[channel] for pixel in samples)[len(samples) // 2] for channel in range(3))
    difference = ImageChops.difference(rgb, Image.new("RGB", rgb.size, background))
    red, green, blue = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    return maximum.point(lambda value: 255 if value > 18 else 0).getbbox()


def ensure_crop_in_bounds(crop: tuple[int, int, int, int], size: tuple[int, int], asset_id: str) -> None:
    left, top, right, bottom = crop
    width, height = size
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError(f"{asset_id}: crop {crop} is outside source bounds {size}")


def ensure_safe_placement(placement: tuple[int, int, int, int], asset_id: str) -> None:
    x, y, width, height = placement
    left, top, right, bottom = SAFE_AREA
    if not (left <= x and top <= y and x + width <= right and y + height <= bottom):
        raise ValueError(f"{asset_id}: placement {placement} leaves the universal safe area {SAFE_AREA}")


def remove_connected_neutral_background(image: Image.Image) -> Image.Image:
    """Remove only edge-connected pale neutral background from Mama's source.

    The photographed food, wrapper, and shadow are protected because this is a
    connectivity mask: enclosed pale packaging is never selected from the edge.
    """
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    candidate = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            red, green, blue, _ = pixels[x, y]
            if min(red, green, blue) > 220 and max(red, green, blue) - min(red, green, blue) <= 9:
                candidate[y * width + x] = 1

    connected = bytearray(width * height)
    queue: list[tuple[int, int]] = []
    for x in range(width):
        queue.extend(((x, 0), (x, height - 1)))
    for y in range(1, height - 1):
        queue.extend(((0, y), (width - 1, y)))

    for x, y in queue:
        index = y * width + x
        if candidate[index]:
            connected[index] = 1

    position = 0
    while position < len(queue):
        x, y = queue[position]
        position += 1
        for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= next_x < width and 0 <= next_y < height:
                index = next_y * width + next_x
                if candidate[index] and not connected[index]:
                    connected[index] = 1
                    queue.append((next_x, next_y))

    for y in range(height):
        for x in range(width):
            if connected[y * width + x]:
                red, green, blue, _ = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0)
    return rgba


def normalize(asset: dict[str, Any]) -> dict[str, Any]:
    source_path = ROOT / "public" / "assets" / "menu" / asset["source"]
    output_path = OUTPUT_DIR / asset["output"]

    with Image.open(source_path) as source_file:
        source_file.load()
        source_rgba = source_file.convert("RGBA")
        source_bounds = foreground_bounds(source_file)
        source_alpha = source_rgba.getchannel("A").getextrema()
        source_size = source_file.size
        source_format = source_file.format
        source_mode = source_file.mode

    crop = tuple(asset["crop"])
    placement = tuple(asset["placement"])
    ensure_crop_in_bounds(crop, source_size, asset["id"])
    ensure_safe_placement(placement, asset["id"])

    cropped = source_rgba.crop(crop)
    if asset["id"] == "mamas-original-single":
        cropped = remove_connected_neutral_background(cropped)
    _, _, placed_width, placed_height = placement
    resized = cropped.resize((placed_width, placed_height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS_SIZE, (255, 255, 255, 255))
    canvas.alpha_composite(resized, (placement[0], placement[1]))
    output_rgb = canvas.convert("RGB")
    output_rgb.save(output_path, **WEBP_OPTIONS)

    with Image.open(output_path) as output_file:
        output_file.load()
        output_bounds = foreground_bounds(output_file)
        output_size = output_file.size
        output_format = output_file.format

    crop_width = crop[2] - crop[0]
    crop_height = crop[3] - crop[1]
    return {
        "id": asset["id"],
        "source_file": str(source_path.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(source_path),
        "source_dimensions": list(source_size),
        "source_format": source_format,
        "source_mode": source_mode,
        "source_alpha_extrema": list(source_alpha),
        "detected_visible_bounds": list(source_bounds) if source_bounds else None,
        "manual_crop_bounds": list(crop),
        "crop_dimensions": [crop_width, crop_height],
        "scale_factor": round(placed_width / crop_width, 6),
        "placement": {"x": placement[0], "y": placement[1], "width": placed_width, "height": placed_height},
        "final_rendered_bounds": list(output_bounds) if output_bounds else None,
        "output_file": str(output_path.relative_to(ROOT)).replace("\\", "/"),
        "output_dimensions": list(output_size),
        "output_format": output_format,
        "output_colour_space": "sRGB",
        "output_file_size_bytes": output_path.stat().st_size,
        **({"group": asset["group"]} if "group" in asset else {}),
        **({"manual_review": asset["manual_review"]} if "manual_review" in asset else {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Permit replacing existing normalized outputs.")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = [OUTPUT_DIR / asset["output"] for asset in ASSETS if (OUTPUT_DIR / asset["output"]).exists()]
    if existing and not args.force:
        names = ", ".join(path.name for path in existing)
        raise SystemExit(f"Refusing to overwrite existing outputs: {names}. Re-run with --force after review.")

    records = [normalize(asset) for asset in ASSETS]
    manifest = {
        "canvas": {"width": CANVAS_SIZE[0], "height": CANVAS_SIZE[1], "aspect_ratio": "4:3", "colour_space": "sRGB"},
        "universal_safe_area": {"left": SAFE_AREA[0], "top": SAFE_AREA[1], "right": SAFE_AREA[2], "bottom": SAFE_AREA[3]},
        "output_format": "WebP quality=95 method=6",
        "assets": records,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(MANIFEST_PATH.relative_to(ROOT)), "asset_count": len(records)}, indent=2))


if __name__ == "__main__":
    main()
