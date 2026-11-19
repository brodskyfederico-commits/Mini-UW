"""Verify a bounded synthetic permanent-bank PDF revision and its debt-yield addendum."""
import base64
import binascii
from copy import deepcopy
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from check_operating_replay_D20 import require
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_debt_yield_D178 import bank_debt_yield_terms
from worksheet_evidence_pdf_D156 import PROFILE, read_evidence_pdf
from worksheet_local_sources_D127 import object_or_empty, synthetic_id


MAX_PDF_BYTES = 32_768
MUTABLE = {"annual_nominal_rate", "amortization_years", "maximum_ltv", "minimum_dscr"}
FIELDS = {"source_ref", "revision", "parent_document_id", "parent_sha256", "pdf_sha256", "pdf_base64",
          "parent_addendum_sha256", "debt_yield_addendum"}


def support_inventory(raw, cells):
    records = object_or_empty(raw)
    individual = object_or_empty(records.get("individual"))
    require(records.keys() == {"individual", "combined"} and individual.keys() == set(cells)
            and all(isinstance(record, dict) for record in (*individual.values(), records.get("combined"))),
            "permanent_support_inventory_invalid")
    return records


def supported_terms(record, name, raw, parent):
    require(isinstance(raw, dict) and isinstance(parent, dict) and not parent.get("blockers") and parent.get("document"),
            "permanent_support_verified_parent_required")
    require(isinstance(record, dict) and record.keys() == FIELDS
            and synthetic_id(record["source_ref"]) and synthetic_id(record["revision"])
            and record["revision"] != parent["revision"]
            and record["parent_document_id"] == parent["document_id"]
            and record["parent_sha256"] == parent["source_sha256"], "permanent_support_parent_or_revision_unconfirmed")
    text = record["pdf_base64"]
    require(isinstance(text, str) and 0 < len(text) <= 4*((MAX_PDF_BYTES+2)//3), "permanent_support_pdf_size_invalid")
    try:
        pdf = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("permanent_support_pdf_encoding_invalid") from None
    require(0 < len(pdf) <= MAX_PDF_BYTES and sha(pdf) == record["pdf_sha256"], "permanent_support_pdf_hash_mismatch")
    try:
        reader = PdfReader(BytesIO(pdf), strict=True)
        require(not reader.is_encrypted and len(reader.pages) == 1, "permanent_support_requires_one_page")
    except (PyPdfError, OSError, TypeError, NotImplementedError):
        raise ValueError("permanent_support_pdf_unreadable") from None
    inventory, pages = read_evidence_pdf(pdf, dict(profile=PROFILE, sha256=record["pdf_sha256"]), record["revision"], raw.get("deal_id"))
    quote = object_or_empty(pages.get(f"bank_{name}"))
    require(not inventory["blockers"] and quote and not quote["blockers"] and quote.get("page") == 1,
            "permanent_support_pdf_scope_or_rows_unconfirmed")
    unchanged = lambda terms: {key: value for key, value in terms.items() if key not in MUTABLE}
    require(unchanged(quote["document"]) == unchanged(parent["document"]), "permanent_support_changes_other_contract_terms")
    old = object_or_empty(object_or_empty(raw.get("bank_debt_yield")).get(name))
    bank_debt_yield_terms(raw.get("bank_debt_yield"), name, parent)
    new = object_or_empty(record["debt_yield_addendum"])
    require(record["parent_addendum_sha256"] == sha(encoded(old)) and synthetic_id(new.get("source_ref"))
            and new["source_ref"] != old["source_ref"], "permanent_support_addendum_parent_unconfirmed")
    terms_only = lambda item: {key: value for key, value in item.items() if key not in {"source_ref", "quote_document_id", "quote_source_sha256"}}
    require(terms_only(new) == terms_only(old), "permanent_support_changes_debt_yield_terms")
    bank_debt_yield_terms({name: new}, name, quote)
    locator = f"case.json#permanent_support/{record['pdf_sha256']}/pdf"
    quote = quote | dict(source_file=locator, extraction_method="pdf_text",
        locators={key: value.replace("Evidence.pdf", locator, 1) for key, value in quote["locators"].items()},
        parent_document_id=parent["document_id"], parent_source_sha256=parent["source_sha256"], support_source_ref=record["source_ref"])
    inputs = deepcopy(raw)
    inputs["bank_debt_yield"][name] = new
    proof = {key: value for key, value in record.items() if key != "pdf_base64"}
    return quote, inputs, proof | dict(observed_pdf_sha256=sha(pdf), origin_inputs_sha256=sha(encoded(raw)), method="pdf_text")
