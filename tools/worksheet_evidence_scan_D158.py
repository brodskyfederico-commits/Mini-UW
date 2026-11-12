"""Read financial evidence from the visible grayscale raster and reconcile a text overlay."""
from decimal import Decimal

from miniuw_foundation.scheduled_expense_case import sha
from worksheet_evidence_pdf_D156 import SOURCE_FILE, parse_page
from worksheet_local_sources_D127 import check
from worksheet_plan_mixed_D132 import PAGE_ERRORS, text_lines
from worksheet_plan_scan_D131 import full_page_image, recognize, runtime


PROFILE = "SYNTHETIC-D158-scanned-financial-evidence"


def financial_ocr_command(options):
    command, blocker = runtime(options)
    if blocker:
        return None, blocker
    args, env = command
    # Financial pages in this profile are one left-aligned text block.
    args = list(args)
    args[args.index("--psm") + 1] = "6"
    return (args, env), None


def page_role(lines, headers):
    markers = [line for line in lines if line in headers]
    return headers[lines[0]] if lines and markers == [lines[0]] else None


def scanned_evidence_page(page, number, digest, revision, deal_id, headers, options, command):
    citation = dict(source_file=SOURCE_FILE, source_sha256=digest, page=number)
    role = None
    try:
        native = [line.strip() for line in (page.extract_text() or "").splitlines() if line.strip()]
        if sum(map(len, native)) > 4096:
            return None, check("evidence_scan_text_layer_too_large", **citation)
        native_role = page_role(native, headers)
        image = full_page_image(page, allow_text_layer=True)
        if image is None:
            if native_role == "official_snapshot" and text_lines(page) is not None:
                return native_role, parse_page(native_role, number, native[1:], digest, revision, deal_id)
            return native_role, check("evidence_financial_scan_required_or_layout_unsupported", **citation)
        rows = sorted(recognize(image, *command), key=lambda row: tuple(row["pixel_region"][i] for i in (1, 0)))
        raster = [row["text"] for row in rows]
        role = page_role(raster, headers)
        minimum = options["minimum_word_confidence"]
        evidence = citation | dict(extraction_method="text_and_ocr" if native else "ocr",
                                   ocr_input_sha256=sha(image), ocr=dict(minimum_word_confidence_required=minimum,
                                                                        cited_lines=rows))
        if len(rows) > 24 or sum(map(len, raster)) > 4096:
            return None, check("evidence_scan_ocr_output_unsupported", **citation)
        if role is None or (native_role is not None and native_role != role):
            return None, check("evidence_scan_page_role_missing_or_disagrees_with_text",
                               ocr_role=role, text_role=native_role, text_lines=native, **evidence)
        parsed = parse_page(role, number, raster[1:], digest, revision, deal_id)
        if any(Decimal(row["minimum_word_confidence"]) < minimum for row in rows):
            return role, check("evidence_scan_ocr_confidence_below_declared_minimum", **evidence)
        if native:
            native_parsed = (parse_page(role, number, native[1:], digest, revision, deal_id) if native_role == role
                             else check("evidence_text_page_role_unverified", text_lines=native))
            if parsed["blockers"] or native_parsed["blockers"]:
                return role, check("evidence_scan_both_readings_required",
                                   readings=dict(ocr=parsed, text=native_parsed), **evidence)
            comparable = ("document_id", "revision", "deal_id", "document")
            if any(parsed[key] != native_parsed[key] for key in comparable):
                return role, check("evidence_scan_and_text_disagree",
                                   readings=dict(ocr=parsed, text=native_parsed), **evidence)
            evidence["text_observation"] = native_parsed["observations"]
        return role, parsed | evidence
    except PAGE_ERRORS:
        return role, check("evidence_scan_ocr_or_image_unreadable", **citation)
