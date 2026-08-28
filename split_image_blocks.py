"""Split a composite image into numbered JPEG blocks.

Example:
    python split_image_blocks.py composite.jpg --output-dir blocks
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops


def trim_block(block: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    """Remove uniform border space from a block while keeping a small margin."""
    background_image = Image.new("RGB", block.size, background)
    difference = ImageChops.difference(block, background_image)
    bounding_box = difference.getbbox()
    if bounding_box is None:
        return block

    left, top, right, bottom = bounding_box
    margin = 4
    return block.crop(
        (
            max(0, left - margin),
            max(0, top - margin),
            min(block.width, right + margin),
            min(block.height, bottom + margin),
        )
    )


def split_image(
    source: Path,
    output_dir: Path,
    columns: int = 4,
    rows: int = 2,
    count: int = 7,
    trim: bool = True,
    quality: int = 95,
) -> list[Path]:
    """Split *source* row by row and save up to *count* blocks as JPEG files."""
    if columns < 1 or rows < 1 or count < 1 or count > columns * rows:
        raise ValueError("count must be between 1 and columns * rows")

    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    with Image.open(source) as image:
        image = image.convert("RGB")
        cell_width = image.width // columns
        cell_height = image.height // rows

        for index in range(count):
            row, column = divmod(index, columns)
            left = column * cell_width
            top = row * cell_height
            right = image.width if column == columns - 1 else (column + 1) * cell_width
            bottom = image.height if row == rows - 1 else (row + 1) * cell_height
            block = image.crop((left, top, right, bottom))
            if trim:
                block = trim_block(block, block.getpixel((0, 0)))

            destination = output_dir / f"block_{index + 1:02d}.jpg"
            block.save(destination, format="JPEG", quality=quality, optimize=True)
            saved_paths.append(destination)

    return saved_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Split one image into numbered JPEG blocks.")
    parser.add_argument("image", type=Path, help="Composite image to split")
    parser.add_argument("--output-dir", type=Path, default=Path("split_blocks"))
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--count", type=int, default=7)
    parser.add_argument("--quality", type=int, choices=range(1, 101), default=95)
    parser.add_argument("--no-trim", action="store_true", help="Keep the complete grid cells")
    args = parser.parse_args()

    for path in split_image(
        args.image,
        args.output_dir,
        columns=args.columns,
        rows=args.rows,
        count=args.count,
        trim=not args.no_trim,
        quality=args.quality,
    ):
        print(path)


if __name__ == "__main__":
    main()