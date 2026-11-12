"""Extract the visible pixels of a bounded synthetic grayscale PDF scan."""
from fractions import Fraction

from worksheet_plan_overlay_D133 import rotate_scan


def visible_crop(page, raster, rotation):
    """Return cropped and full oriented PGM data with an exact pixel locator."""
    _, dimensions, maximum, _ = raster.split(b"\n", 3)
    width, height = map(int, dimensions.split())
    page_width = Fraction(str(page.mediabox.width))
    page_height = Fraction(str(page.mediabox.height))
    if page_width <= 0 or page_height <= 0:
        return None
    left, bottom, right, top = (Fraction(str(coordinate)) for coordinate in page.cropbox)
    if not (0 <= left < right <= page_width and 0 <= bottom < top <= page_height):
        return None
    pixel_edges = (left * width / page_width, height - top * height / page_height,
                   right * width / page_width, height - bottom * height / page_height)
    if any(edge.denominator != 1 for edge in pixel_edges):
        return None
    x0, y0, x1, y1 = map(int, pixel_edges)
    if rotation == 90:
        x0, y0, x1, y1 = height - y1, x0, height - y0, x1
    elif rotation == 180:
        x0, y0, x1, y1 = width - x1, height - y1, width - x0, height - y0
    elif rotation == 270:
        x0, y0, x1, y1 = y0, width - x1, y1, width - x0

    full = rotate_scan(raster, rotation) if rotation else raster
    _, dimensions, _, pixels = full.split(b"\n", 3)
    stride = int(dimensions.split()[0])
    cropped = b"".join(pixels[y * stride + x0:y * stride + x1] for y in range(y0, y1))
    visible = f"P5\n{x1 - x0} {y1 - y0}\n".encode() + maximum + b"\n" + cropped
    return visible, full, dict(crop_box_pdf_points=[str(value) for value in (left, bottom, right, top)],
                               crop_region_in_oriented_scan=[x0, y0, x1, y1])


def citations_inside(cited_lines, region):
    left, top, right, bottom = region
    return all(left <= x0 < x1 <= right and top <= y0 < y1 <= bottom
               for x0, y0, x1, y1 in (line["pixel_region"] for line in cited_lines))
