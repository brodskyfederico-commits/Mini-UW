"""Compare PDF text with OCR of the underlying image on the same synthetic sheet."""
from io import BytesIO

from pypdf import PdfReader

from miniuw_foundation.scheduled_expense_case import sha
from worksheet_local_sources_D127 import check, object_or_empty, synthetic_id
from worksheet_plan_mixed_D132 import PAGE_ERRORS, matching_sheet_identity, read_mixed_sheet
from worksheet_plan_pdf_D130 import SUMMARY_ROW, sheet_area, unavailable_plan
from worksheet_plan_scan_D131 import full_page_image, recognize, runtime, scan_reading, valid_ocr_options


PROFILE = "SYNTHETIC-D133-compare-text-with-underlying-image"
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


def image_observation(page, ocr, digest, plan_ref):
    citation = dict(page=PAGE, sheet=SHEET, extraction_method="ocr", source_sha256=digest)
    try:
        image = full_page_image(page, allow_text_layer=True)
        if image is None:
            return check("overlay_image_layout_unsupported_or_missing", **citation)
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


def read_overlay_sheet(page, ocr, digest, plan_ref):
    native = text_observation(page, digest, plan_ref)
    image = image_observation(page, ocr, digest, plan_ref)
    evidence = dict(sheet=SHEET, page=PAGE, extraction_method="text_and_ocr", source_sha256=digest,
                    observations={"text": native, "ocr": image})
    if native["blockers"] or image["blockers"]:
        return check("overlay_both_observations_required", **evidence)
    if any(native[key] != image[key] for key in ("value", "unit", "plan_ref")):
        return check("overlay_observations_conflict", **evidence)
    return native | evidence


def read_overlay_plan(raw, specification):
    spec = object_or_empty(specification)
    if raw is None:
        return unavailable_plan("plan_pdf_missing")
    digest = sha(raw)
    plan_ref = spec.get("plan_ref")
    if digest != spec.get("sha256") or not synthetic_id(plan_ref):
        return unavailable_plan("plan_pdf_hash_or_reference_mismatch", digest)
    ocr = object_or_empty(spec.get("ocr"))
    if spec.get("overlay_profile") != PROFILE or spec.get("page_routes") != ROUTES or not valid_ocr_options(ocr):
        return unavailable_plan("explicit_overlay_sheet_route_and_ocr_profile_required", digest)
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or len(reader.pages) != 2:
            return unavailable_plan("overlay_plan_layout_unsupported", digest)
        first, second = reader.pages
    except PAGE_ERRORS:
        return unavailable_plan("plan_pdf_unreadable", digest)
    return dict(document=check(kind="synthetic_pdf_with_text_overlay", source_file="Plan.pdf", sha256=digest,
                               plan_ref=plan_ref, page_routes=ROUTES, ocr=ocr | {"language": "eng"}),
                B05=read_mixed_sheet(first, "A101", ROUTES["A101"], ocr, digest, plan_ref),
                B06=read_overlay_sheet(second, ocr, digest, plan_ref))
