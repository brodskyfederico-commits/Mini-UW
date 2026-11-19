"""Read a bounded synthetic construction-term PDF linked to the verified parent quote."""
import base64
import binascii
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from check_operating_replay_D20 import require
from miniuw_foundation.scheduled_expense_case import sha
from worksheet_evidence_pdf_D156 import CONSTRUCTION_PROFILE, read_evidence_pdf
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


MAX_PDF_BYTES = 32_768
MUTABLE = {"ltc", "annual_interest", "origination_fee_fraction"}
FIELDS = {"source_ref", "revision", "parent_document_id", "parent_sha256", "pdf_sha256", "pdf_base64"}


def support_inventory(raw, cells):
    records = object_or_empty(raw)
    individual = object_or_empty(records.get("individual"))
    require(records.keys() == {"individual", "combined"} and individual.keys() == set(cells)
            and all(isinstance(record, dict) for record in (*individual.values(), records.get("combined"))),
            "construction_support_inventory_invalid")
    return records


def supported_quote(record, name, deal_id, parent):
    require(isinstance(parent, dict) and not parent.get("blockers") and parent.get("document"),
            "construction_support_verified_parent_required")
    require(isinstance(record, dict) and record.keys() == FIELDS
            and synthetic_id(record["source_ref"]) and synthetic_id(record["revision"])
            and record["revision"] != parent["revision"]
            and record["parent_document_id"] == parent["document_id"]
            and record["parent_sha256"] == parent["source_sha256"], "construction_support_parent_or_revision_unconfirmed")
    text = record["pdf_base64"]
    require(isinstance(text, str) and 0 < len(text) <= 4*((MAX_PDF_BYTES+2)//3), "construction_support_pdf_size_invalid")
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("construction_support_pdf_encoding_invalid") from None
    require(0 < len(raw) <= MAX_PDF_BYTES and sha(raw) == record["pdf_sha256"], "construction_support_pdf_hash_mismatch")
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        require(not reader.is_encrypted and len(reader.pages) == 1, "construction_support_requires_one_page")
    except (PyPdfError, OSError, TypeError, NotImplementedError):
        raise ValueError("construction_support_pdf_unreadable") from None
    inventory, pages = read_evidence_pdf(raw, dict(profile=CONSTRUCTION_PROFILE, sha256=record["pdf_sha256"]),
                                        record["revision"], deal_id, include_construction=True)
    quote = object_or_empty(pages.get(f"construction_{name}"))
    require(not inventory["blockers"] and quote and not quote["blockers"] and quote.get("page") == 1,
            "construction_support_pdf_scope_or_rows_unconfirmed")
    unchanged = lambda terms: {key: value for key, value in terms.items() if key not in MUTABLE}
    require(unchanged(quote["document"]) == unchanged(parent["document"]),
            "construction_support_changes_other_contract_terms")
    locator = f"case.json#construction_support/{record['pdf_sha256']}/pdf"
    quote = quote | dict(source_file=locator, extraction_method="pdf_text",
                         locators={key: value.replace("Evidence.pdf", locator, 1) for key, value in quote["locators"].items()},
                         parent_document_id=parent["document_id"], parent_source_sha256=parent["source_sha256"],
                         support_source_ref=record["source_ref"])
    binding = {key: value for key, value in record.items() if key != "pdf_base64"}
    return quote, binding | dict(observed_pdf_sha256=sha(raw), method="pdf_text")
