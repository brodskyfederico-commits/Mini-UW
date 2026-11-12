"""Compare PDF text with OCR of the underlying image on the same synthetic sheet."""
from io import BytesIO

from pypdf import PdfReader

from miniuw_foundation.scheduled_expense_case import sha
from worksheet_local_sources_D127 import check, object_or_empty, synthetic_id
from worksheet_plan_mixed_D132 import PAGE_ERRORS, matching_sheet_identity, read_mixed_sheet
from worksheet_plan_pdf_D130 import SUMMARY_ROW, sheet_area, unavailable_plan
from worksheet_plan_scan_D131 import full_page_image, recognize, runtime, scan_reading, valid_ocr_options


PROFILE = "SYNTHETIC-D133-compare-text-with-underlying-image"
ROTATED_PROFILE = "SYNTHETIC-D134-oriented-overlay"
RIGHT_ANGLES = (90, 180, 270)
ROUTES = {"A101": {"page": 1, "method": "text"}, "A601": {"page": 2, "method": "text_and_ocr"}}
SHEET = "A601"
PAGE = 2
LABEL = "Declared GBA"


def text_observation(page, digest, plan_ref):
    citation = dict(page=PAGE, sheet=SHEET, extraction_method="text", source_sha256=digest)
    try:
        lines = [line.strip() for line in (page.extract_text() or "").splitlines()]
        if not matching_sheet_identity(lines, SHEET):
            return check("overlay_text_sheet_identity_missing_or_ambiguous", **citation)
        return sheet_area([(PAGE, lines)], SHEET, LABEL, SUMMARY_ROW, digest, plan_ref) | citation
    except PAGE_ERRORS:
        return check("overlay_text_unreadable", **citation)


def rotate_scan(image, clockwise):
    """Rotate the bounded grayscale raster without resampling its pixels."""
    _, dimensions, maximum, pixels = image.split(b"\n", 3)
    width, height = map(int, dimensions.split())
    if clockwise == 180:
        return f"P5\n{width} {height}\n".encode() + maximum + b"\n" + pixels[::-1]
    if clockwise == 90:
        rotated = b"".join(pixels[column::width][::-1] for column in range(width))
    else:
        rotated = b"".join(pixels[column::width] for column in reversed(range(width)))
    return f"P5\n{height} {width}\n".encode() + maximum + b"\n" + rotated


def image_observation(page, ocr, digest, plan_ref, rotation):
    citation = dict(page=PAGE, sheet=SHEET, extraction_method="ocr", source_sha256=digest)
    try:
        if rotation is not None:
            raw_rotation = page.get("/Rotate", 0)
            observed = int(raw_rotation) if isinstance(raw_rotation, int) else None
            citation.update(declared_page_rotation=rotation, observed_page_rotation=observed)
            if observed != rotation:
                return check("overlay_page_rotation_mismatch", **citation)
        image = full_page_image(page, allow_text_layer=True, allowed_rotation=rotation or 0)
        if image is None:
            return check("overlay_image_layout_unsupported_or_missing", **citation)
        if rotation is not None:
            citation.update(raw_image_sha256=sha(image), ocr_region_basis="rotation_normalized_pixels")
            image = rotate_scan(image, rotation)
        citation["ocr_input_sha256"] = sha(image)
        command, blocker = runtime(ocr)
        if blocker:
            return check(blocker, **citation)
        recognized = recognize(image, *command)
        if not matching_sheet_identity([line["text"] for line in recognized], SHEET):
            return check("overlay_image_sheet_identity_missing_or_ambiguous", **citation)
        return scan_reading([(PAGE, recognized)], SHEET, LABEL, SUMMARY_ROW, digest, plan_ref,
                            ocr["minimum_word_confidence"]) | citation
    except PAGE_ERRORS:
        return check("overlay_image_ocr_unreadable", **citation)


def read_overlay_sheet(page, ocr, digest, plan_ref, rotation):
    native = text_observation(page, digest, plan_ref)
    image = image_observation(page, ocr, digest, plan_ref, rotation)
    evidence = dict(sheet=SHEET, page=PAGE, extraction_method="text_and_ocr", source_sha256=digest,
                    observations={"text": native, "ocr": image})
    if native["blockers"] or image["blockers"]:
        return check("overlay_both_observations_required", **evidence)
    if any(native[key] != image[key] for key in ("value", "unit", "plan_ref")):
        return check("overlay_observations_conflict", **evidence)
    return native | evidence


def read_overlay_plan(raw, specification, *, require_rotation=False):
    spec = object_or_empty(specification)
    if raw is None:
        return unavailable_plan("plan_pdf_missing")
    digest = sha(raw)
    plan_ref = spec.get("plan_ref")
    if digest != spec.get("sha256") or not synthetic_id(plan_ref):
        return unavailable_plan("plan_pdf_hash_or_reference_mismatch", digest)
    ocr = object_or_empty(spec.get("ocr"))
    profile = ROTATED_PROFILE if require_rotation else PROFILE
    if spec.get("overlay_profile") != profile or spec.get("page_routes") != ROUTES or not valid_ocr_options(ocr):
        return unavailable_plan("explicit_overlay_sheet_route_and_ocr_profile_required", digest)
    rotation = None
    if require_rotation:
        rotation = spec.get("page_rotation_clockwise")
        if type(rotation) is not int or rotation not in RIGHT_ANGLES:
            return unavailable_plan("explicit_overlay_page_rotation_required", digest)
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or len(reader.pages) != 2:
            return unavailable_plan("overlay_plan_layout_unsupported", digest)
        first, second = reader.pages
    except PAGE_ERRORS:
        return unavailable_plan("plan_pdf_unreadable", digest)
    document = check(kind="synthetic_pdf_with_text_overlay", source_file="Plan.pdf", sha256=digest,
                     plan_ref=plan_ref, page_routes=ROUTES, ocr=ocr | {"language": "eng"})
    if require_rotation:
        document.update(kind="synthetic_rotated_pdf_with_text_overlay", page_rotation_clockwise=rotation)
    return dict(document=document,
                B05=read_mixed_sheet(first, "A101", ROUTES["A101"], ocr, digest, plan_ref),
                B06=read_overlay_sheet(second, ocr, digest, plan_ref, rotation))
