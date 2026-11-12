"""Read a synthetic mixed plan with an explicit extraction method for each sheet."""
from decimal import InvalidOperation
from io import BytesIO
from subprocess import SubprocessError

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from miniuw_foundation.scheduled_expense_case import sha
from worksheet_local_sources_D127 import check, object_or_empty, synthetic_id
from worksheet_plan_pdf_D130 import MARKER, SUMMARY_ROW, TABLE_ROW, sheet_area, unavailable_plan
from worksheet_plan_scan_D131 import full_page_image, recognize, runtime, scan_reading, valid_ocr_options


PROFILE = "SYNTHETIC-D132-mixed-text-and-scan"
SHEETS = {"A101": ("B05", "Gross building area", TABLE_ROW), "A601": ("B06", "Declared GBA", SUMMARY_ROW)}
PAGE_ERRORS = (PyPdfError, OSError, ValueError, TypeError, KeyError, SubprocessError, InvalidOperation, NotImplementedError)


def valid_routes(routes):
    if routes.keys() != SHEETS.keys():
        return False
    for row in routes.values():
        if (not isinstance(row, dict) or set(row) != {"page", "method"} or type(row["page"]) is not int
                or row["page"] not in (1, 2) or row["method"] not in ("text", "ocr")):
            return False
    return {row["page"] for row in routes.values()} == {1, 2} and {row["method"] for row in routes.values()} == {"text", "ocr"}


def text_lines(page):
    resources = page["/Resources"] if "/Resources" in page else {}
    xobjects = resources.get("/XObject")
    contents = page.get_contents()
    if (contents is None or xobjects is not None and xobjects.get_object()
            or any(op in (b"Do", b"INLINE IMAGE") for _, op in contents.operations)
            or page.rotation != 0 or tuple(page.cropbox) != tuple(page.mediabox)):
        return None
    return [line.strip() for line in (page.extract_text() or "").splitlines()]


def read_mixed_sheet(page, sheet, route, ocr, digest, plan_ref):
    index, method = route["page"], route["method"]
    citation = dict(sheet=sheet, page=index, extraction_method=method, source_sha256=digest)
    _, label, pattern = SHEETS[sheet]
    try:
        if method == "text":
            lines = text_lines(page)
            if lines is None:
                return check("mixed_text_page_layout_unsupported", **citation)
        else:
            image = full_page_image(page)
            if image is None:
                return check("mixed_ocr_page_layout_unsupported", **citation)
            command, blocker = runtime(ocr)
            if blocker:
                return check(blocker, **citation)
            recognized = recognize(image, *command)
            lines = [line["text"] for line in recognized]
        if lines.count(MARKER) != 1 or [line for line in lines if line.startswith("SHEET ")] != [f"SHEET {sheet}"]:
            return check("mixed_sheet_identity_missing_or_ambiguous", **citation)
        if method == "text":
            return sheet_area([(index, lines)], sheet, label, pattern, digest, plan_ref) | citation
        return scan_reading([(index, recognized)], sheet, label, pattern, digest, plan_ref,
                            ocr["minimum_word_confidence"]) | citation
    except PAGE_ERRORS:
        return check("mixed_page_unreadable", **citation)


def read_mixed_plan(raw, specification):
    spec = object_or_empty(specification)
    if raw is None:
        return unavailable_plan("plan_pdf_missing")
    digest = sha(raw)
    plan_ref = spec.get("plan_ref")
    if digest != spec.get("sha256") or not synthetic_id(plan_ref):
        return unavailable_plan("plan_pdf_hash_or_reference_mismatch", digest)
    routes, ocr = (object_or_empty(spec.get(name)) for name in ("page_routes", "ocr"))
    if spec.get("mixed_profile") != PROFILE or not valid_routes(routes) or not valid_ocr_options(ocr):
        return unavailable_plan("explicit_mixed_sheet_routes_and_ocr_profile_required", digest)
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or len(reader.pages) != 2:
            return unavailable_plan("mixed_plan_layout_unsupported", digest)
        pages = list(reader.pages)
    except PAGE_ERRORS:
        return unavailable_plan("plan_pdf_unreadable", digest)
    readings = {bot: read_mixed_sheet(pages[routes[sheet]["page"] - 1], sheet, routes[sheet], ocr, digest, plan_ref)
                for sheet, (bot, _, _) in SHEETS.items()}
    return readings | {"document": check(kind="synthetic_mixed_pdf_plan", source_file="Plan.pdf", sha256=digest,
                                        plan_ref=plan_ref, page_routes=routes, ocr=ocr | {"language": "eng"})}
