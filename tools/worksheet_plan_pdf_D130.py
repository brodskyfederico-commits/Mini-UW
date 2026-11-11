"""Read explicitly printed area values from two sheets of a synthetic PDF plan."""
from fractions import Fraction
from io import BytesIO
import re

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from miniuw_foundation.debt_service import rational
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_local_sources_D127 import check, object_or_empty, synthetic_id


MARKER = "SYNTHETIC MINI-UW PLAN"
TABLE_ROW = re.compile(r"Gross building area\s*\|\s*([0-9]{1,12}(?:\.[0-9]{1,6})?)\s*\|\s*m2")
SUMMARY_ROW = re.compile(r"Declared GBA:\s*((?:[0-9]{1,12}|[0-9]{1,3}(?:,[0-9]{3}){1,3})(?:\.[0-9]{1,6})?)\s+m2")


def sheet_area(pages, sheet, label, pattern, digest, plan_ref):
    matches = [(index, lines) for index, lines in pages if f"SHEET {sheet}" in lines]
    if len(matches) != 1:
        return check("required_sheet_missing_or_ambiguous", sheet=sheet)
    index, lines = matches[0]
    if lines.count(f"SHEET {sheet}") != 1:
        return check("required_sheet_missing_or_ambiguous", sheet=sheet, page=index)
    refs = [line for line in lines if line.startswith("PLAN REF ")]
    if refs != [f"PLAN REF {plan_ref}"]:
        return check("plan_reference_missing_or_mismatched", sheet=sheet, page=index)
    rows = [line for line in lines if line.startswith(label)]
    if len(rows) != 1:
        return check("explicit_area_missing_or_ambiguous", sheet=sheet, page=index, raw_observations=rows)
    matched = pattern.fullmatch(rows[0])
    amount = None if matched is None else Fraction(matched[1].replace(",", ""))
    if amount is None or amount <= 0:
        return check("area_value_or_unit_unsupported", sheet=sheet, page=index, raw_observations=rows)
    return check(value=rational(amount), unit="m2", plan_ref=plan_ref, document_id=plan_ref,
                 source_sha256=digest, source_file="Plan.pdf", sheet=sheet, page=index,
                 locator=f"p. {index} / {sheet} / {label}", raw_line=rows[0])


def unavailable_plan(blocker, digest=None):
    return dict(document=check(blocker, source_file="Plan.pdf", observed_sha256=digest),
                B05=check("bound_synthetic_plan_pdf_required"), B06=check("bound_synthetic_plan_pdf_required"))


def read_plan(raw, specification):
    spec = object_or_empty(specification)
    if raw is None:
        return unavailable_plan("plan_pdf_missing")
    digest = sha(raw)
    if digest != spec.get("sha256") or not synthetic_id(spec.get("plan_ref")):
        return unavailable_plan("plan_pdf_hash_or_reference_mismatch", digest)
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 12:
            return unavailable_plan("plan_pdf_profile_unsupported", digest)
        pages = []
        for index, page in enumerate(reader.pages, 1):
            lines = [line.strip() for line in (page.extract_text() or "").splitlines()]
            if MARKER in lines:
                pages.append((index, lines))
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, NotImplementedError):
        return unavailable_plan("plan_pdf_unreadable", digest)
    if not pages:
        return unavailable_plan("synthetic_text_plan_not_identified", digest)
    plan_ref = spec["plan_ref"]
    return dict(document=check(kind="synthetic_pdf_plan", source_file="Plan.pdf", sha256=digest, plan_ref=plan_ref),
                B05=sheet_area(pages, "A101", "Gross building area", TABLE_ROW, digest, plan_ref),
                B06=sheet_area(pages, "A601", "Declared GBA", SUMMARY_ROW, digest, plan_ref))
