"""Read and reconcile the declared data of an architectural PDF set."""

from collections import Counter, defaultdict
import csv
from decimal import Decimal
from hashlib import file_digest
import re

from worksheet_plan_checklist import plan_preflight, plan_values
from worksheet_preliminary_D185 import SCENARIOS


MAX_PAGES = 200
MAX_PDF_BYTES = 256 * 1024 * 1024
TYPES = ("STUDIO", "1 BEDROOM", "2 BEDROOM", "3 BEDROOM")
AREA = r"(?:[1-9][0-9]{0,2}(?:,[0-9]{3})+|[1-9][0-9]*|0)(?:\.[0-9]+)?"
SQUARE_FEET = r"(?:S\.?\s*F\.?|SQ\.?\s*FT\.?)"
SHEET_TITLE = re.compile(r"(?m)^((?:A|G)[0-9]+\.[0-9]+)[ \t]*\n\1[ \t]*$")
FLOOR_INDEX = re.compile(r"(?m)^(A2\.[0-9]+)\n\1\nPROPOSED (?:[^\n]+ FLOOR|ROOF) PLAN$")
UNIT_ID = r"[A-Z]-[0-9]{3,4}"
UNIT_TYPE = r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*"
UNIT = re.compile(rf"(?m)^({UNIT_ID})\nUNIT TYPE ({UNIT_TYPE})\n({'|'.join(TYPES)})$")


def read_pdf(path):
    try:
        import pymupdf
    except ImportError as error:
        raise ValueError("El ingreso documental requiere PyMuPDF.") from error
    if not 0 < path.stat().st_size <= MAX_PDF_BYTES:
        raise ValueError(f"{path.name}: tamaño fuera del perfil documental.")
    with path.open("rb") as stream:
        digest = file_digest(stream, "sha256").hexdigest()
    try:
        with pymupdf.open(path) as pdf:
            if not pdf.is_pdf or pdf.needs_pass or not 1 <= len(pdf) <= MAX_PAGES:
                raise ValueError(f"{path.name}: PDF cifrado o inventario fuera del perfil documental.")
            pages = ["\n".join(line.strip() for line in page.get_text().splitlines() if line.strip()) for page in pdf]
    except pymupdf.FileDataError as error:
        raise ValueError(f"{path.name}: PDF ilegible.") from error
    return {"file": path.name, "sha256": digest, "pages": len(pages)}, pages


def read_site(text):
    building = re.search(
        rf"(?m)^BUILDING DATA\nMULTI-FAMILY RESIDENTIAL\nOFFICE\nRETAIL\nRESTAURANT\nOPEN SPACE\nPROVIDED\n"
        rf"([0-9]+) UNITS\n({AREA}) {SQUARE_FEET}\n({AREA}) {SQUARE_FEET}\n({AREA}) {SQUARE_FEET}$", text
    )
    unit_table = re.search(r"(?ms)^UNIT DATA\n(.+?)^TOTAL UNITS\s*\(([0-9]+) UNITS\)\n--\n([0-9]+)\n([0-9]+)$", text)
    if not building or not unit_table:
        return None
    mix = re.findall(r"(?m)^(STUDIO|[123]-BEDROOM)\s*\(([0-9]+) UNITS\)$", unit_table[1])
    if sorted(kind.replace("-", " ") for kind, _ in mix) != sorted(TYPES):
        return None
    return {
        "building_units": int(building[1]),
        "units": int(unit_table[2]),
        "affordable_units": int(unit_table[3]),
        "market_units": int(unit_table[4]),
        "unit_mix": {kind.replace("-", " "): int(count) for kind, count in mix},
        "commercial_areas_sf": {name: Decimal(value.replace(",", "")) for name, value in
                                zip(("office", "retail", "restaurant"), building.groups()[1:])},
    }


def commercial_claims(pages, filename, pattern):
    claims = []
    for page, content in enumerate(pages, 1):
        flattened = " ".join(content.split())
        for match in re.finditer(pattern, flattened, re.I):
            claims.append({"file": filename, "page": page, "area_sf": Decimal(match[1].replace(",", "")),
                           "literal": match[0]})
    return claims


def read_area_schedule(path):
    with path.open("rb") as stream:
        digest = file_digest(stream, "sha256").hexdigest()
    rows = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["unit_type", "area_sf"]:
            raise ValueError("El cuadro de áreas requiere encabezados unit_type,area_sf.")
        for row in reader:
            kind, area = (row[key] or "" for key in reader.fieldnames)
            kind, area = kind.strip().upper(), area.strip()
            if set(row) != set(reader.fieldnames) or not re.fullmatch(UNIT_TYPE, kind) or kind in rows:
                raise ValueError(f"Tipo de unidad inválido o duplicado en línea {reader.line_num}.")
            if not re.fullmatch(AREA, area) or Decimal(area.replace(",", "")) <= 0:
                raise ValueError(f"Área inválida en línea {reader.line_num}.")
            rows[kind] = {"area_sf": str(Decimal(area.replace(",", ""))), "line": reader.line_num}
    return {"file": path.name, "sha256": digest, "unit_types": rows}


def intake(architecture, *, narrative=None, area_schedule=None):
    source, pages = read_pdf(architecture)
    findings = []

    def flag(code, **evidence):
        findings.append({"code": code, **evidence})

    sheets = defaultdict(list)
    for page, content in enumerate(pages, 1):
        if "SHEET INDEX" in content.splitlines() and "G0.0" in SHEET_TITLE.findall(content):
            sheets["G0.0"].append(page)
            continue
        candidates = set(SHEET_TITLE.findall(content))
        if len(candidates) == 1:
            sheets[candidates.pop()].append(page)
        elif any(sheet == "A1.0" or sheet.startswith("A2.") for sheet in candidates):
            flag("ambiguous_sheet", page=page, candidates=sorted(candidates))

    def required(sheet):
        matches = sheets[sheet]
        if len(matches) != 1:
            flag("missing_sheet" if not matches else "duplicate_sheet", sheet=sheet, pages=matches)
            return None
        return matches[0]

    cover = required("G0.0")
    floor_ids = set(FLOOR_INDEX.findall(pages[cover - 1])) if cover else set()
    if not floor_ids:
        flag("floor_index_missing", sheet="G0.0", page=cover)
    else:
        for sheet in sorted(sheets.keys() - floor_ids):
            if sheet.startswith("A2."):
                flag("unlisted_floor_sheet", sheet=sheet, pages=sheets[sheet])

    site_page = required("A1.0")
    site = read_site(pages[site_page - 1]) if site_page else None
    if site_page and site is None:
        flag("site_tables_unreadable", sheet="A1.0", page=site_page)

    floor_units = []
    for sheet in sorted(floor_ids, key=lambda value: int(value.split(".")[1])):
        page = required(sheet)
        if page is None:
            continue
        content = pages[page - 1]
        parsed = UNIT.findall(content)
        labels = len(re.findall(r"(?m)^UNIT TYPE\b", content))
        if labels != len(parsed):
            flag("incomplete_unit_labels", sheet=sheet, page=page, labels=labels, parsed=len(parsed))
        floor_units.extend({"id": unit, "unit_type": kind, "bedrooms": bedrooms, "sheet": sheet, "page": page}
                           for unit, kind, bedrooms in parsed)

    unit_locations = defaultdict(list)
    for unit in floor_units:
        unit_locations[unit["id"]].append(unit)
    for key, occurrences in sorted(unit_locations.items()):
        if len(occurrences) > 1:
            flag("duplicate_unit_id", unit_id=key, occurrences=occurrences)
    floor_mix = Counter(unit["bedrooms"] for unit in floor_units)

    claims = []
    if cover:
        claims = commercial_claims([pages[cover - 1]], source["file"],
                                   rf"CONSISTING OF ({AREA}) {SQUARE_FEET} OF RETAIL\s*/\s*OFFICE")
        if not claims:
            flag("cover_area_unreadable", sheet="G0.0", page=cover)
        for claim in claims:
            claim.update(page=cover, sheet="G0.0")
    sources = {"architecture": source}
    if narrative:
        sources["narrative"], letter = read_pdf(narrative)
        narrative_claims = commercial_claims(letter, narrative.name,
                                             rf"PROPOSED TO BE REPLACED BY A MIXED-USE DEVELOPMENT CONSISTING OF ({AREA})\s*"
                                             rf"{SQUARE_FEET} OF RETAIL\s*/\s*OFFICE")
        if not narrative_claims:
            flag("narrative_area_unreadable", file=narrative.name)
        claims.extend(narrative_claims)

    if site:
        reported_total = site["units"]
        for basis, observed in {"building_data": site["building_units"], "unit_mix": sum(site["unit_mix"].values()),
                                "affordability_split": site["affordable_units"] + site["market_units"],
                                "floor_labels": len(floor_units), "floor_unique_ids": len(unit_locations)}.items():
            if observed != reported_total:
                flag("unit_total_mismatch", basis=basis, site_page=site_page, declared=reported_total, observed=observed)
        for kind, declared in site["unit_mix"].items():
            if declared != floor_mix[kind]:
                floor_pages = sorted({unit["page"] for unit in floor_units if unit["bedrooms"] == kind})
                flag("unit_mix_mismatch", bedrooms=kind, site_page=site_page, floor_pages=floor_pages,
                     declared=declared, observed=floor_mix[kind])
        site_total = sum(site["commercial_areas_sf"].values())
        claims.insert(0, {"file": source["file"], "page": site_page, "sheet": "A1.0", "area_sf": site_total,
                          "literal": "BUILDING DATA / OFFICE + RETAIL + RESTAURANT"})
        for claim in claims[1:]:
            if claim["area_sf"] != site_total:
                flag("commercial_area_mismatch", site_page=site_page, site_area_sf=str(site_total),
                     claim={**claim, "area_sf": str(claim["area_sf"])}, difference_sf=str(claim["area_sf"] - site_total))
        site["commercial_areas_sf"] = {key: str(value) for key, value in site["commercial_areas_sf"].items()}
        site.update(page=site_page, commercial_total_sf=str(site_total))

    if area_schedule:
        schedule = sources["area_schedule"] = read_area_schedule(area_schedule)
        for kind in sorted({row["unit_type"] for row in floor_units} - schedule["unit_types"].keys()):
            flag("unit_area_missing", unit_type=kind, occurrences=[row for row in floor_units if row["unit_type"] == kind])
    else:
        flag("unit_area_schedule_missing")

    preflight = plan_preflight(findings)
    verified = plan_values(preflight, site, floor_units, sources.get("area_schedule", {}).get("unit_types", {}))
    return_blockers = preflight["calculations"]["return_per_usd_10"]["plan_blockers"]
    return {
        "profile": "miniuw.documentary-intake.v1", "sources": sources, "preflight": preflight,
        "plan": {"site": site, "floor_sheets": {key: sheets[key] for key in sorted(floor_ids)},
                 "floor_labels": len(floor_units), "unique_unit_ids": len(unit_locations), "floor_mix": dict(floor_mix),
                 "units": floor_units, "commercial_claims": [{**claim, "area_sf": str(claim["area_sf"])} for claim in claims],
                 "findings": findings, "verified_inputs": verified, "state": preflight["status"]},
        "state": "PENDING", "decision": "PENDING", "ranking": [], "deployment_enabled": False,
        "real_decisions_enabled": False, "personal_investor_return": None,
        "scenarios": {name: {"state": "PENDING", "cash": None, "return_per_usd_10": "PENDING",
                             "plan_blockers": return_blockers,
                             "blockers": ["documentary_intake_only", "verified_financial_inputs_missing"]}
                      for name in SCENARIOS},
    }
