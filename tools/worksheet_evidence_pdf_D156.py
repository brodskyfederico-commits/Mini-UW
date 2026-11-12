"""Read bounded synthetic GC, bank and archived official evidence from explicit PDF rows."""
from fractions import Fraction
from io import BytesIO
from subprocess import SubprocessError
import re

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from miniuw_foundation.debt_service import _fraction, rational
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded
from worksheet_construction_financing_D146 import RULES as CONSTRUCTION_RULES
from worksheet_local_sources_D127 import SCHEMA_PREFIX, check, object_or_empty, synthetic_id


PROFILE = "SYNTHETIC-D156-evidence-pdf"
CONSTRUCTION_PROFILE = "SYNTHETIC-D157-evidence-pdf-with-construction"
SOURCE_FILE = "Evidence.pdf"
SCOPE = "vertical_building_excluding_parking_and_site"
HEADERS = {
    "SYNTHETIC MINI-UW GC QUOTE": "gc_budget",
    "SYNTHETIC MINI-UW BANK TERMS BASE": "bank_Base",
    "SYNTHETIC MINI-UW BANK TERMS DOWNSIDE": "bank_Downside",
    "SYNTHETIC MINI-UW OFFICIAL COPY": "official_snapshot",
}
CONSTRUCTION_HEADERS = {
    "SYNTHETIC MINI-UW CONSTRUCTION TERMS BASE": "construction_Base",
    "SYNTHETIC MINI-UW CONSTRUCTION TERMS DOWNSIDE": "construction_Downside",
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
CONSTRUCTION_ROWS = {
    "C51": ("ltc", "fraction"),
    "C52": ("annual_interest", "annual_nominal_fraction"),
    "C53": ("origination_fee_fraction", "fraction_of_commitment"),
    "Maximum commitment": ("maximum_commitment", "USD"),
    "Requested invoice share": ("requested_invoice_fraction", "fraction"),
    "Available per draw": ("available_per_draw_checkpoint", "USD"),
}
CONSTRUCTION_CONVENTIONS = {
    "Eligible cost": CONSTRUCTION_RULES["eligible_cost"],
    "Commitment basis": CONSTRUCTION_RULES["commitment"],
    "Draw basis": CONSTRUCTION_RULES["draws"],
    "Interest basis": CONSTRUCTION_RULES["interest"],
    "Fee basis": CONSTRUCTION_RULES["fee"],
    "Payoff basis": CONSTRUCTION_RULES["payoff"],
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
        elif role.startswith("construction_"):
            if fields != CONSTRUCTION_ROWS.keys() | CONSTRUCTION_CONVENTIONS.keys() | {"Maturity date"} or any(
                    literal(key) != value for key, value in CONSTRUCTION_CONVENTIONS.items()):
                raise ValueError("construction_pdf_convention_or_inventory_unconfirmed")
            document = {field: parse_quantity(rows[key], unit) for key, (field, unit) in CONSTRUCTION_ROWS.items()}
            document["maturity_date"] = literal("Maturity date")
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


def read_evidence_pdf(raw, spec, revision, deal_id, *, include_construction=False, scanned=False,
                      oriented=False, allow_rgb=False, jpeg_profile=None):
    headers = HEADERS | CONSTRUCTION_HEADERS if include_construction else HEADERS
    profile = CONSTRUCTION_PROFILE if include_construction else PROFILE
    required = {"profile", "sha256"}
    if scanned:
        from worksheet_evidence_scan_D158 import COLOR_PROFILE, ORIENTED_PROFILE, PROFILE as scan_profile
        from worksheet_evidence_scan_D158 import financial_ocr_command, scanned_evidence_page
        from worksheet_plan_scan_D131 import valid_ocr_options
        profile = COLOR_PROFILE if allow_rgb else ORIENTED_PROFILE if oriented else scan_profile
        required.add("ocr")
    if jpeg_profile:
        from worksheet_evidence_jpeg_D161 import PROFILE as sequential_profile, PROGRESSIVE_PROFILE, jpeg_runtime
        profile = PROGRESSIVE_PROFILE if jpeg_profile == "D162" else sequential_profile
        required.add("jpeg_decoder")
    specification = object_or_empty(spec)
    digest = None if raw is None else sha(raw)
    inventory = dict(source_file=SOURCE_FILE, observed_sha256=digest)
    error = None
    if raw is None:
        error = "evidence_pdf_missing"
    elif (specification.keys() != required or specification["profile"] != profile
          or specification["sha256"] != digest or not synthetic_id(revision) or not synthetic_id(deal_id)):
        error = "evidence_pdf_binding_unconfirmed"
    if error:
        return check(error, **inventory), {}
    if jpeg_profile:
        decoder = jpeg_runtime()
        if decoder is None:
            return check("evidence_jpeg_decoder_unavailable", **inventory), {}
        if specification["jpeg_decoder"] != decoder:
            return check("evidence_jpeg_decoder_mismatch", **inventory), {}
        inventory["jpeg_decoder"] = decoder
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= len(headers):
            return check("evidence_pdf_profile_unsupported", **inventory), {}
        pages = {}
        if scanned:
            options = object_or_empty(specification.get("ocr"))
            if not valid_ocr_options(options):
                return check("evidence_scan_ocr_profile_invalid", **inventory), {}
            command, blocker = financial_ocr_command(options)
            if blocker:
                return check(blocker, **inventory), {}
            inventory["ocr"] = options | dict(language="eng", page_segmentation_mode=6)
        for number, page in enumerate(reader.pages, 1):
            if scanned:
                role, reading = scanned_evidence_page(page, number, digest, revision, deal_id, headers, options, command,
                                                      oriented=oriented, allow_rgb=allow_rgb, jpeg_profile=jpeg_profile)
                if role is None:
                    return check(reading["blockers"][0], page_reading=reading, **inventory), {}
            else:
                text = page.extract_text() or ""
                if len(text) > 4096:
                    return check("evidence_pdf_profile_unsupported", **inventory), {}
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                role = headers.get(lines[0]) if lines else None
                if role is None or any(line in headers for line in lines[1:]):
                    return check("evidence_page_role_unrecognized_or_ambiguous", page=number, **inventory), {}
                reading = parse_page(role, number, lines[1:], digest, revision, deal_id)
            if role in pages:
                return check("evidence_page_role_duplicate", role=role, **inventory), {}
            pages[role] = reading
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, NotImplementedError, SubprocessError):
        return check("evidence_pdf_unreadable", **inventory), {}
    missing = set(headers.values()) - pages.keys()
    for role in sorted(missing):
        pages[role] = check("evidence_page_role_missing", **inventory)
    return check(kind=profile, page_roles={role: entry.get("page") for role, entry in pages.items()}, **inventory), pages


def bind_document_terms(quote, candidate, mismatch):
    if quote["blockers"]:
        return quote

    def exact(value):
        if isinstance(value, dict):
            return _fraction(value)
        return value

    conflicts = sorted(key for key, value in quote["document"].items() if exact(value) != exact(candidate[key]))
    if conflicts:
        return check(mismatch, fields=conflicts, quote=quote)
    return check(quote=quote)


def bind_bank_evidence(quote, terms, principal):
    return bind_document_terms(quote, terms | {"requested_principal": rational(principal)},
                               "bank_pdf_and_worksheet_terms_disagree")


def pdf_document_sources(source, raw, deal_id, *, include_construction=False, scanned=False,
                         oriented=False, allow_rgb=False, jpeg_profile=None):
    inventory, pages = read_evidence_pdf(raw, source.get("evidence_pdf"), source.get("revision"), deal_id,
                                         include_construction=include_construction, scanned=scanned,
                                         oriented=oriented, allow_rgb=allow_rgb, jpeg_profile=jpeg_profile)
    if "documents" in source:
        inventory = check("structured_document_sources_conflict_with_pdf_profile",
                          source_file=SOURCE_FILE, observed_sha256=inventory["observed_sha256"])
        pages = {}
    documents = {role: dict(document=pages[role]["document"], sha256=sha(encoded(pages[role]["document"])))
                 for role in ("gc_budget", "official_snapshot") if role in pages and not pages[role]["blockers"]}
    return source | {"documents": documents}, inventory, pages


def record_pdf_evidence(review, inventory, pages, *, include_construction=False):
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
        for name, quote in budget.get("scenario_quotes", {}).items():
            if not quote["blockers"]:
                quote["normalized_document_sha256"] = quote["source_sha256"]
                quote.update(source_sha256=gc["source_sha256"], source_file=SOURCE_FILE, page=gc["page"])
                if "ocr" in gc:
                    quote.update(extraction_method=gc["extraction_method"], ocr_input_sha256=gc["ocr_input_sha256"],
                                 ocr_citation=next(row for row in gc["ocr"]["cited_lines"]
                                                   if row["text"].startswith(f"Vertical {name} | ")))
                    for key in ("page_rotation_clockwise", "raw_image_sha256", "ocr_region_basis",
                                "crop_box_pdf_points", "crop_region_in_oriented_scan", "full_oriented_scan_sha256",
                                "source_color_space", "source_raster_sha256", "grayscale_conversion", "grayscale_input_sha256",
                                "source_image_filter", "source_jpeg_sha256", "jpeg_encoding"):
                        if key in gc:
                            quote[key] = gc[key]
    official = pages.get("official_snapshot")
    if official is not None:
        for key in ("B10", "B11"):
            bots[key]["official_pdf"] = {name: value for name, value in official.items() if name != "document"}
        if official["blockers"]:
            review["blockers"].extend(f"B10:{reason}" for reason in official["blockers"])
        if not bots["B11"]["blockers"] and not official["blockers"]:
            bots["B11"].update(document_locator=official["locators"]["Record"], document_sha256=official["source_sha256"])
    roles = ("bank", "construction") if include_construction else ("bank",)
    for role in roles:
        quotes = {name: pages.get(f"{role}_{name}", check(f"bound_{role}_pdf_page_required"))
                  for name in ("Base", "Downside")}
        budget[f"{role}_pdf_by_scenario"] = quotes
        for name, quote in quotes.items():
            if quote["blockers"]:
                budget["state"] = "PENDING"
                review["blockers"].extend(f"B08:{name}:{reason}" for reason in quote["blockers"])
    if review["blockers"]:
        review["state"] = "PENDING"
