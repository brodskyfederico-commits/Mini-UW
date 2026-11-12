"""Discover required sheets across a bounded synthetic PDF and verify their areas."""
from collections import defaultdict
from decimal import Decimal
from io import BytesIO
import re

from pypdf import PdfReader

from miniuw_foundation.scheduled_expense_case import sha
from worksheet_local_sources_D127 import check, object_or_empty, synthetic_id
from worksheet_plan_crop_D138 import citations_inside, visible_crop
from worksheet_plan_mixed_D132 import PAGE_ERRORS, SHEETS, text_lines
from worksheet_plan_overlay_D133 import RIGHT_ANGLES, rotate_scan
from worksheet_plan_pdf_D130 import MARKER, sheet_area, unavailable_plan
from worksheet_plan_scan_D131 import full_page_image, recognize, runtime, scan_reading, valid_ocr_options


PROFILE = "SYNTHETIC-D135-sheet-set"
ROTATED_PROFILE = "SYNTHETIC-D136-rotated-sheet-set"
DUAL_ROTATED_PROFILE = "SYNTHETIC-D137-two-rotated-sheets"
CROPPED_PROFILE = "SYNTHETIC-D138-cropped-rotated-sheets"
MAX_PAGES = 12
SHEET_ID = re.compile(r"SHEET ([A-Z][A-Z0-9.-]{0,23})")


def observe_identity(lines, plan_ref, *, ocr_rows=(), threshold=0):
    claims = [line for line in lines if line.startswith("SHEET ")]
    refs = [line for line in lines if line.startswith("PLAN REF ")]
    markers = lines.count(MARKER)
    names = [match[1] for line in claims if (match := SHEET_ID.fullmatch(line))]
    evidence = dict(sheet_claims=names, plan_references=refs, raw_sheet_lines=claims)
    if len(claims) != 1 or len(names) != 1 or refs != [f"PLAN REF {plan_ref}"] or markers != 1:
        return check("sheet_identity_or_plan_reference_unverified", **evidence)
    if ocr_rows:
        headings = [MARKER, *refs, *claims]
        cited = [row for row in ocr_rows if row["text"] in headings]
        evidence["cited_lines"] = cited
        if len(cited) != 3 or any(Decimal(row["minimum_word_confidence"]) < threshold for row in cited):
            return check("sheet_identity_ocr_confidence_insufficient", **evidence)
    return check(sheet=names[0], **evidence)


def identify_page(page, index, ocr, plan_ref, *, allow_rotation=False, allow_crop_box=False):
    sources, observations = {}, {}
    raster_evidence = {}
    try:
        native = text_lines(page)
        if native is not None:
            sources["text"] = native
        else:
            rotation = page.get("/Rotate", 0) if allow_rotation else 0
            if not isinstance(rotation, int) or rotation not in (0, *RIGHT_ANGLES):
                return check("sheet_page_rotation_unsupported", page=index), sources
            raster = full_page_image(page, allow_text_layer=True, allowed_rotation=rotation, allow_crop_box=allow_crop_box)
            if raster is None:
                return check("sheet_page_layout_unsupported", page=index), sources
            native = [line.strip() for line in (page.extract_text() or "").splitlines() if line.strip()]
            if native:
                sources["text"] = native
            full_oriented = None
            if allow_rotation:
                raster_evidence.update(page_rotation_clockwise=int(rotation), raw_image_sha256=sha(raster),
                                       ocr_region_basis="rotation_normalized_pixels")
                if allow_crop_box and tuple(page.cropbox) != tuple(page.mediabox):
                    cropped = visible_crop(page, raster, rotation)
                    if cropped is None:
                        return check("scan_crop_box_unsupported", page=index), sources
                    raster, full_oriented, crop_evidence = cropped
                    raster_evidence.update(crop_evidence, full_oriented_scan_sha256=sha(full_oriented),
                                           ocr_region_basis="cropped_rotation_normalized_pixels")
                elif rotation:
                    raster = rotate_scan(raster, rotation)
            raster_evidence["ocr_input_sha256"] = sha(raster)
            command, blocker = runtime(ocr)
            if blocker:
                observations["ocr"] = check(blocker, **raster_evidence)
            else:
                rows = recognize(raster, *command)
                sources["ocr"] = rows
                threshold = ocr["minimum_word_confidence"]
                identity = observe_identity([row["text"] for row in rows], plan_ref, ocr_rows=rows, threshold=threshold)
                if full_oriented is not None and not identity["blockers"]:
                    full_rows = recognize(full_oriented, *command)
                    full_identity = observe_identity([row["text"] for row in full_rows], plan_ref, ocr_rows=full_rows,
                                                     threshold=threshold)
                    if (full_identity["blockers"] or full_identity["sheet"] != identity["sheet"]
                            or not citations_inside(full_identity["cited_lines"], raster_evidence["crop_region_in_oriented_scan"])):
                        identity.update(check("scan_crop_hides_or_changes_sheet_identity"))
                    sources["uncropped_ocr"] = full_rows
                observations["ocr"] = identity | raster_evidence
        if "text" in sources:
            observations["text"] = observe_identity(sources["text"], plan_ref)
    except PAGE_ERRORS:
        return check("sheet_page_unreadable", page=index, observations=observations), sources
    evidence = dict(page=index, observations=observations)
    if any(row["blockers"] for row in observations.values()):
        return check("sheet_page_identity_unverified", **evidence), sources
    sheets = {row["sheet"] for row in observations.values()}
    if len(sheets) != 1:
        return check("sheet_page_identities_conflict", **evidence), sources
    return check(sheet=next(iter(sheets)), **evidence), sources


def required_reading(sheet, pages, claimed, document, digest, plan_ref, threshold, *, expected_rotation=None):
    evidence = dict(sheet=sheet, candidate_pages=claimed)
    if len(claimed) > 1:
        return check("required_sheet_duplicated", **evidence)
    if document["blockers"]:
        return check("sheet_inventory_incomplete", **evidence)
    if not claimed:
        return check("required_sheet_missing", **evidence)
    index, = claimed
    identity, sources = pages[index - 1]
    _, label, pattern = SHEETS[sheet]
    readings = {}
    if "text" in sources:
        readings["text"] = sheet_area([(index, sources["text"])], sheet, label, pattern, digest, plan_ref)
    if "ocr" in sources:
        ocr_evidence = identity["observations"]["ocr"]
        raster_keys = ("ocr_input_sha256", "page_rotation_clockwise", "raw_image_sha256", "ocr_region_basis",
                       "crop_box_pdf_points", "crop_region_in_oriented_scan", "full_oriented_scan_sha256")
        readings["ocr"] = scan_reading([(index, sources["ocr"])], sheet, label, pattern, digest, plan_ref, threshold)
        readings["ocr"].update({key: ocr_evidence[key] for key in raster_keys if key in ocr_evidence})
        reading = readings["ocr"]
        if "uncropped_ocr" in sources and not reading["blockers"]:
            full = scan_reading([(index, sources["uncropped_ocr"])], sheet, label, pattern, digest, plan_ref, threshold)
            if (full["blockers"] or full["raw_line"] != reading["raw_line"]
                    or not citations_inside(full["ocr"]["cited_lines"], reading["crop_region_in_oriented_scan"])):
                reading["ocr"]["observed_value"] = reading.pop("value")
                reading.update(check("scan_crop_hides_or_changes_required_area"))
    for method, row in readings.items():
        row.update(extraction_method=method, source_sha256=digest, page=index)
    method = "text_and_ocr" if len(readings) == 2 else next(iter(readings))
    evidence.update(page=index, extraction_method=method, source_sha256=digest, observations=readings)
    if expected_rotation is not None:
        observed = readings.get("ocr", {}).get("page_rotation_clockwise")
        evidence.update(declared_page_rotation=expected_rotation, observed_page_rotation=observed)
        if method != "text_and_ocr":
            return check("rotated_sheet_text_and_ocr_required", **evidence)
        if observed != expected_rotation:
            return check("required_sheet_page_rotation_mismatch", **evidence)
    if any(row["blockers"] for row in readings.values()):
        return check("required_sheet_area_unverified", **evidence)
    first = next(iter(readings.values()))
    if any(row["value"] != first["value"] for row in readings.values()):
        return check("required_sheet_area_observations_conflict", **evidence)
    return first | evidence


def read_plan_set(raw, specification, *, profile=PROFILE):
    spec = object_or_empty(specification)
    if raw is None:
        return unavailable_plan("plan_pdf_missing")
    digest = sha(raw)
    plan_ref = spec.get("plan_ref")
    if digest != spec.get("sha256") or not synthetic_id(plan_ref):
        return unavailable_plan("plan_pdf_hash_or_reference_mismatch", digest)
    ocr = object_or_empty(spec.get("ocr"))
    if spec.get("sheet_set_profile") != profile or not valid_ocr_options(ocr):
        return unavailable_plan("explicit_sheet_set_and_ocr_profile_required", digest)
    expected_rotations = {}
    if profile == ROTATED_PROFILE:
        rotation = spec.get("a601_rotation_clockwise")
        if type(rotation) is not int or rotation not in RIGHT_ANGLES:
            return unavailable_plan("explicit_a601_page_rotation_required", digest)
        expected_rotations["A601"] = rotation
    elif profile in (DUAL_ROTATED_PROFILE, CROPPED_PROFILE):
        expected_rotations = object_or_empty(spec.get("sheet_rotations_clockwise"))
        if expected_rotations.keys() != SHEETS.keys() or any(
                type(angle) is not int or angle not in RIGHT_ANGLES for angle in expected_rotations.values()):
            return unavailable_plan("explicit_required_sheet_rotations_required", digest)
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PAGES:
            return unavailable_plan("plan_pdf_profile_unsupported", digest)
        pages = [identify_page(page, index, ocr, plan_ref, allow_rotation=bool(expected_rotations),
                               allow_crop_box=profile == CROPPED_PROFILE)
                 for index, page in enumerate(reader.pages, 1)]
    except PAGE_ERRORS:
        return unavailable_plan("plan_pdf_unreadable", digest)

    inventory = [identity for identity, _ in pages]
    candidates = defaultdict(list)
    for identity in inventory:
        claims = {name for observation in identity.get("observations", {}).values()
                  for name in observation.get("sheet_claims", ())}
        for sheet in sorted(claims):
            candidates[sheet].append(identity["page"])
    duplicates = {sheet: indices for sheet, indices in candidates.items() if len(indices) > 1}
    if any(row["blockers"] for row in inventory):
        blocker = "plan_sheet_inventory_incomplete"
    else:
        blocker = "plan_sheet_duplicates" if duplicates else None
    document = check(blocker, kind="synthetic_pdf_sheet_set", source_file="Plan.pdf", sha256=digest,
                     plan_ref=plan_ref, sheet_inventory=inventory, duplicate_sheet_pages=duplicates,
                     ocr=ocr | {"language": "eng"})
    if profile == ROTATED_PROFILE:
        document.update(kind="synthetic_rotated_pdf_sheet_set", a601_rotation_clockwise=expected_rotations["A601"])
    elif profile == DUAL_ROTATED_PROFILE:
        document.update(kind="synthetic_pdf_sheet_set_with_two_rotations", sheet_rotations_clockwise=expected_rotations)
    elif profile == CROPPED_PROFILE:
        document.update(kind="synthetic_pdf_sheet_set_with_cropped_scans", sheet_rotations_clockwise=expected_rotations)
    return {"document": document} | {
        bot: required_reading(sheet, pages, candidates[sheet], document, digest, plan_ref, ocr["minimum_word_confidence"],
                              expected_rotation=expected_rotations.get(sheet))
        for sheet, (bot, _, _) in SHEETS.items()}
