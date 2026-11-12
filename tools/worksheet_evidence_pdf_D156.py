"""Read bounded synthetic GC, bank and archived official evidence from explicit PDF rows."""
from fractions import Fraction
from io import BytesIO
import re

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_local_sources_D127 import SCHEMA_PREFIX, check, object_or_empty, synthetic_id


PROFILE = "SYNTHETIC-D156-evidence-pdf"
SOURCE_FILE = "Evidence.pdf"
SCOPE = "vertical_building_excluding_parking_and_site"
HEADERS = {
    "SYNTHETIC MINI-UW GC QUOTE": "gc_budget",
    "SYNTHETIC MINI-UW BANK TERMS BASE": "bank_Base",
    "SYNTHETIC MINI-UW BANK TERMS DOWNSIDE": "bank_Downside",
    "SYNTHETIC MINI-UW OFFICIAL COPY": "official_snapshot",
}
METADATA = {"Document ID", "Revision", "Case ID"}
BANK_ROWS = {
    "Requested principal": ("requested_principal", "USD"),
    "C69": ("annual_nominal_rate", "annual_nominal_fraction"),
    "C70": ("amortization_years", "years"),
    "C71": ("maximum_ltv", "fraction"),
    "C72": ("minimum_dscr", "multiple"),
    "Payments per year": ("payments_per_year", "payments/year"),
    "Maturity": ("maturity_payments", "payments"),
}
BANK_CONVENTIONS = {
    "Interest basis": "nominal_annual_fixed_convertible_quarterly",
    "Payment timing": "regular_in_arrears",
    "Capacity limits": "LTV+DSCR",
}
DECIMAL = re.compile(r"[0-9]{1,12}(?:\.[0-9]{1,8})?")


def parse_quantity(parts, unit):
    if len(parts) != 2 or parts[0] != unit or DECIMAL.fullmatch(parts[1]) is None:
        raise ValueError("evidence_value_or_unit_incompatible")
    return rational(Fraction(parts[1]))


def parse_page(role, number, lines, digest, revision, deal_id):
    citation = dict(source_file=SOURCE_FILE, source_sha256=digest, page=number)
    try:
        rows = {}
        for line in lines:
            key, *parts = line.split(" | ")
            if not parts or key in rows or any(not part for part in parts):
                raise ValueError("evidence_row_malformed_or_duplicate")
            rows[key] = parts

        def literal(key):
            value, = rows[key]
            return value

        if (literal("Revision") != revision or literal("Case ID") != deal_id
                or not synthetic_id(literal("Document ID"))):
            raise ValueError("evidence_case_or_revision_mismatch")
        document_id = literal("Document ID")
        locators = {key: f"{SOURCE_FILE} p. {number} / {key}" for key in rows}
        provenance = citation | dict(document_id=document_id, revision=revision, deal_id=deal_id,
                                     locators=locators, observations=rows)
        fields = rows.keys() - METADATA
        common = dict(document_id=document_id, revision=revision)
        if role == "gc_budget":
            if fields != {"Plan REF", "Area", "Vertical Base", "Vertical Downside"} or not synthetic_id(literal("Plan REF")):
                raise ValueError("gc_pdf_scope_or_inventory_unconfirmed")
            quotes = {}
            for name in ("Base", "Downside"):
                key = f"Vertical {name}"
                scope, *value = rows[key]
                if scope != SCOPE:
                    raise ValueError("gc_pdf_scope_or_inventory_unconfirmed")
                quotes[name] = dict(scope=scope, currency="USD", value=parse_quantity(value, "USD"), locator=locators[key])
            document = common | dict(schema=f"{SCHEMA_PREFIX}gc_budget.v1", plan_ref=literal("Plan REF"),
                                     area=dict(value=parse_quantity(rows["Area"], "m2"), unit="m2", locator=locators["Area"]),
                                     budget_by_scenario=quotes)
        elif role == "official_snapshot":
            if fields != {"URL", "Valid from", "Valid through", "Record"}:
                raise ValueError("official_pdf_record_inventory_unconfirmed")
            record_id, *value = rows["Record"]
            floors = _fraction(parse_quantity(value, "floors"))
            if not synthetic_id(record_id) or floors.denominator != 1:
                raise ValueError("official_pdf_record_incompatible")
            document = common | dict(schema=f"{SCHEMA_PREFIX}official_snapshot.v1", url=literal("URL"),
                                     valid_from=literal("Valid from"), valid_through=literal("Valid through"),
                                     records={record_id: {"max_floors": int(floors)}})
        else:
            if fields != BANK_ROWS.keys() | BANK_CONVENTIONS.keys() or any(
                    literal(key) != value for key, value in BANK_CONVENTIONS.items()):
                raise ValueError("bank_pdf_convention_or_inventory_unconfirmed")
            document = {field: parse_quantity(rows[key], unit) for key, (field, unit) in BANK_ROWS.items()}
        return check(document=document, **provenance)
    except ValueError as error:
        return check(str(error) if re.fullmatch(r"[a-z_]+", str(error)) else "evidence_required_row_invalid", **citation)
    except KeyError:
        return check("evidence_required_row_invalid", **citation)


def read_evidence_pdf(raw, spec, revision, deal_id):
    specification = object_or_empty(spec)
    digest = None if raw is None else sha(raw)
    inventory = dict(source_file=SOURCE_FILE, observed_sha256=digest)
    error = None
    if raw is None:
        error = "evidence_pdf_missing"
    elif (specification.keys() != {"profile", "sha256"} or specification["profile"] != PROFILE
          or specification["sha256"] != digest or not synthetic_id(revision) or not synthetic_id(deal_id)):
        error = "evidence_pdf_binding_unconfirmed"
    if error:
        return check(error, **inventory), {}
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= len(HEADERS):
            return check("evidence_pdf_profile_unsupported", **inventory), {}
        pages = {}
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if len(text) > 4096:
                return check("evidence_pdf_profile_unsupported", **inventory), {}
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            role = HEADERS.get(lines[0]) if lines else None
            if role is None or any(line in HEADERS for line in lines[1:]):
                return check("evidence_page_role_unrecognized_or_ambiguous", page=number, **inventory), {}
            if role in pages:
                return check("evidence_page_role_duplicate", role=role, **inventory), {}
            pages[role] = parse_page(role, number, lines[1:], digest, revision, deal_id)
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, NotImplementedError):
        return check("evidence_pdf_unreadable", **inventory), {}
    missing = set(HEADERS.values()) - pages.keys()
    for role in sorted(missing):
        pages[role] = check("evidence_page_role_missing", **inventory)
    return check(kind=PROFILE, page_roles={role: entry.get("page") for role, entry in pages.items()}, **inventory), pages


def bind_bank_evidence(quote, terms, principal):
    if quote["blockers"]:
        return quote
    candidate = terms | {"requested_principal": rational(principal)}
    conflicts = sorted(key for key, value in quote["document"].items() if _fraction(value) != _fraction(
        rational(candidate[key]) if type(candidate[key]) is int else candidate[key]))
    if conflicts:
        return check("bank_pdf_and_worksheet_terms_disagree", fields=conflicts, quote=quote)
    return check(quote=quote)


def pdf_document_sources(source, raw, deal_id):
    inventory, pages = read_evidence_pdf(raw, source.get("evidence_pdf"), source.get("revision"), deal_id)
    if "documents" in source:
        inventory = check("structured_document_sources_conflict_with_pdf_profile",
                          source_file=SOURCE_FILE, observed_sha256=inventory["observed_sha256"])
        pages = {}
    documents = {role: dict(document=pages[role]["document"], sha256=sha(encoded(pages[role]["document"])))
                 for role in ("gc_budget", "official_snapshot") if role in pages and not pages[role]["blockers"]}
    return source | {"documents": documents}, inventory, pages


def record_pdf_evidence(review, inventory, pages):
    bots = review["bots"]
    classifier = bots["B03"]
    classifier["documents"]["evidence_pdf"] = inventory
    if inventory["blockers"]:
        classifier["state"] = "PENDING"
        classifier["blockers"].extend(inventory["blockers"])
        review["blockers"].extend(f"B03:{reason}" for reason in inventory["blockers"])
    budget = bots["B08"]
    gc = pages.get("gc_budget")
    if gc is not None:
        budget["gc_pdf"] = {key: value for key, value in gc.items() if key != "document"}
        if gc["blockers"]:
            review["blockers"].extend(f"B08:gc_budget:{reason}" for reason in gc["blockers"])
        for quote in budget.get("scenario_quotes", {}).values():
            if not quote["blockers"]:
                quote["normalized_document_sha256"] = quote["source_sha256"]
                quote.update(source_sha256=gc["source_sha256"], source_file=SOURCE_FILE, page=gc["page"])
    official = pages.get("official_snapshot")
    if official is not None:
        for key in ("B10", "B11"):
            bots[key]["official_pdf"] = {name: value for name, value in official.items() if name != "document"}
        if official["blockers"]:
            review["blockers"].extend(f"B10:{reason}" for reason in official["blockers"])
        if not bots["B11"]["blockers"] and not official["blockers"]:
            bots["B11"].update(document_locator=official["locators"]["Record"], document_sha256=official["source_sha256"])
    budget["bank_pdf_by_scenario"] = {name: pages.get(f"bank_{name}", check("bound_bank_pdf_page_required"))
                                      for name in ("Base", "Downside")}
    for name, quote in budget["bank_pdf_by_scenario"].items():
        if quote["blockers"]:
            budget["state"] = "PENDING"
            review["blockers"].extend(f"B08:{name}:{reason}" for reason in quote["blockers"])
    if review["blockers"]:
        review["state"] = "PENDING"
