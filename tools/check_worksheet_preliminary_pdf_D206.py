"""Build and verify the original PRELIMINAR pilot with text PDF source pages."""
from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction as Q
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader, PdfWriter

from check_reference_package import require
from check_worksheet_preliminary_pilot_D205 import DEAL, INDEX, SECOND, fixture as prior_fixture
from check_worksheet_preliminary_tax_D204 import normalized
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_foundation.synthetic_onepager import _pdf, _pdf_string
from miniuw_worksheet_v1 import encoded
from reconcile_worksheet_D179 import exact
from worksheet_preliminary_pilot_D205 import AREAS, SCENARIOS, paths, pilot_audit, pilot_run
from worksheet_preliminary_pdf_D206 import MARKER, ROLES, SCHEMA


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "templates/preliminary-pilot-D206"
ORDER = ("permanent_bank", "A601", "florida_property_tax", "acquisition_and_costs",
         "construction_bank", "calendar", "exit", "A101", "rent_and_expenses")
CONSTRUCTION_DATA = {"construction_commitment_usd", "construction_maturity_date", "construction_stages"}
CONSTRUCTION_CELLS = {"C51", "C52", "C53"}


def leaf_rows(value, prefix=""):
    if isinstance(value, dict):
        for key, child in sorted(value.items()):
            yield from leaf_rows(child, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaf_rows(child, f"{prefix}.[{index}]")
    else:
        literal = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        yield f"Dato | {prefix} | {literal}"


def bundle_pages(deal, scenario, base_files):
    names = paths(deal, scenario)
    records = {area: json.loads(base_files[names[area]]) for area in AREAS}
    records["A101"] = records.pop("program")
    records["A601"] = dict(data={"units": records["A101"]["data"]["units"]}, cells={})
    financing = records.pop("financing")
    for role, is_construction in (("construction_bank", True), ("permanent_bank", False)):
        records[role] = dict(
            data={key: value for key, value in financing["data"].items() if (key in CONSTRUCTION_DATA) == is_construction},
            cells={key: value for key, value in financing["cells"].items() if (key in CONSTRUCTION_CELLS) == is_construction})
    return {role: [MARKER, f"Expediente | {deal}", f"Escenario | {scenario}", f"Rol | {role}",
                   "Tipo | Campo | Valor",
                   *(f"Inputs | {key} | {value}" for key, value in sorted(row["cells"].items())),
                   *leaf_rows(row["data"])] for role, row in records.items()}


def pdf_bundle(pages, order=ORDER):
    writer = PdfWriter()
    for role in order:
        lines = pages[role]
        require(len(lines) <= 57 and max(map(len, lines)) <= 150, "Synthetic table exceeds page bounds")
        commands = [f"BT /F1 8 Tf 1 0 0 1 32 {571 - 9 * i} Tm (".encode() + _pdf_string(line) + b") Tj ET"
                    for i, line in enumerate(lines)]
        if role == "A101":
            # Four simple plan outlines accompany the labeled unit inventory.
            # Vector shapes add no text to the PDF extraction.
            commands.append(b"0.1 0.3 0.45 RG 2 w 48 120 360 215 re S 48 218 m 408 218 l S")
            commands.append(b"204 120 m 204 335 l S 48 195 m 408 195 l S")
        writer.add_page(PdfReader(BytesIO(_pdf(commands)), strict=True).pages[0])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def fixture():
    original = prior_fixture()
    index = json.loads(original[INDEX])
    files = {}
    for deal in index["deals"]:
        for scenario in SCENARIOS:
            names = paths(deal, scenario, pdf=True)
            files[names["Inputs"]] = original[names["Inputs"]]
            files[names["Evidence"]] = pdf_bundle(bundle_pages(deal, scenario, original))
    index.update(schema=SCHEMA, sha256={name: sha(raw) for name, raw in files.items()})
    return files | {INDEX: encoded(index)}


def write_sources(files, directory):
    for name, raw in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def verify(work):
    published = {path.relative_to(FIXTURES).as_posix(): path.read_bytes()
                 for path in FIXTURES.rglob("*") if path.is_file()}
    require(published == fixture(), "Published PDF fixture differs")
    complete = work / "complete"
    result = pilot_run(FIXTURES, complete)
    require(pilot_audit(complete) == result, "The saved package did not replay")
    previous_sources = work / "d205"
    original = prior_fixture()
    write_sources(original, previous_sources)
    prior = pilot_run(previous_sources, work / "prior")
    require(result["ranking"] == prior["ranking"] and result["decision"] == "PENDING"
            and result["state"] == "PRELIMINAR" and not result["real_decisions_enabled"]
            and not result["deployment_enabled"] and not result["full_uw_eligible"], "Ranking or formal decision changed")

    for deal in (DEAL, SECOND):
        for scenario in SCENARIOS:
            view = result["deals"][deal]["scenarios"][scenario]
            require(normalized(view) == normalized(prior["deals"][deal]["scenarios"][scenario]), "Dated USD 10 cash differs")
            pages = view["evidence"]["Evidence"]["pages"]
            require(set(pages) == set(ROLES) and all(pages[role]["page"] == ORDER.index(role) + 1 for role in ROLES)
                    and pages["permanent_bank"]["locators"]["Inputs/C72"] > 5
                    and pages["florida_property_tax"]["locators"]["Dato/rolls.millage.2028.non_school_mills.numerator"] > 5,
                    "PDF citations or page discovery differ")

    page, = PdfReader(complete / "MiniUW_Resumen.pdf").pages
    require(all(text in page.extract_text() for text in ("Dictamen formal PENDING", "29,14", "9,06", "8,95")),
            "Expected one-page cash and formal decision summary")

    original_pages = bundle_pages(DEAL, "Downside", original)
    target = paths(DEAL, "Downside", pdf=True)["Evidence"]

    def change(role, prefix, replacement=None):
        modified = deepcopy(original_pages)
        line, = (line for line in modified[role] if line.startswith(prefix))
        index = modified[role].index(line)
        if replacement is None:
            modified[role].pop(index)
        else:
            modified[role][index] = replacement
        return pdf_bundle(modified)

    variants = {
        "missing-plan-sheet": (pdf_bundle(original_pages, [role for role in ORDER if role != "A601"]), "falta página A601"),
        "plan-conflict": (change("A601", "Dato | units.[1] | ", "Dato | units.[1] | 4"), "A101 y A601 difieren"),
        "missing-quote": (pdf_bundle(original_pages, [role for role in ORDER if role != "acquisition_and_costs"]),
                          "falta página acquisition_and_costs"),
        "duplicate-bank-page": (pdf_bundle(original_pages, [*ORDER, "permanent_bank"]), "rol duplicado permanent_bank"),
        "missing-construction-bank": (pdf_bundle(original_pages, [role for role in ORDER if role != "construction_bank"]),
                                      "falta página construction_bank"),
        "bank-c72-conflict": (change("permanent_bank", "Inputs | C72 | ", "Inputs | C72 | 1.5"), "p. 1 · permanent_bank · C72 difiere"),
        "missing-fiscal-page": (pdf_bundle(original_pages, [role for role in ORDER if role != "florida_property_tax"]),
                                "falta página florida_property_tax"),
        "missing-fiscal-value": (change("florida_property_tax", "Dato | rolls.millage.2028.non_school_mills.numerator | "),
                                 "non_school_mills"),
        "missing-pdf": (None, "archivo ausente"),
        "pdf-hash-changed": (published[target] + b" ", "huella distinta"),
    }
    probes = {}
    for label, (raw, blocker) in variants.items():
        changed = published.copy()
        if raw is None:
            changed.pop(target)
        else:
            changed[target] = raw
            if label != "pdf-hash-changed":
                index = json.loads(changed[INDEX])
                index["sha256"][target] = sha(raw)
                changed[INDEX] = encoded(index)
        source, output = work / f"source-{label}", work / label
        write_sources(changed, source)
        blocked = pilot_run(source, output)
        view = blocked["deals"][DEAL]["scenarios"]
        require(blocked["state"] == blocked["decision"] == "PENDING"
                and [row["deal_id"] for row in blocked["ranking"]] == [SECOND]
                and view["Downside"]["cash"] is None and any(blocker in issue for issue in view["Downside"]["blockers"])
                and view["Base"] == result["deals"][DEAL]["scenarios"]["Base"],
                f"{label}: incorrect evidence gate {view['Downside']['blockers']}")
        require(pilot_audit(output) == blocked, f"{label}: blocked package failed replay")
        probes[label] = view["Downside"]["blockers"]

    # Replace one registered 2028 tax value while retaining the same workbook.
    repriced = published | {target: change("florida_property_tax",
        "Dato | rolls.millage.2028.non_school_mills.numerator | ",
        'Dato | rolls.millage.2028.non_school_mills.numerator | "10"')}
    index = json.loads(repriced[INDEX])
    index["sha256"][target] = sha(repriced[target])
    repriced[INDEX] = encoded(index)
    changed_source = work / "source-tax-change"
    write_sources(repriced, changed_source)
    changed_run = pilot_run(changed_source, work / "tax-change")
    require(pilot_audit(work / "tax-change") == changed_run and changed_run["state"] == "PRELIMINAR",
            "Registered fiscal change did not replay or lost eligibility")
    new = changed_run["deals"][DEAL]["scenarios"]["Downside"]
    before = result["deals"][DEAL]["scenarios"]["Downside"]
    delta = Q(265)
    require(exact(before["financing"]["bank_noi"]) - exact(new["financing"]["bank_noi"]) == delta
            and exact(before["cash"]["total_distributions"]) - exact(new["cash"]["total_distributions"]) == delta / 10500
            and changed_run["ranking"][0]["downside_equity_multiple"] == new["cash"]["equity_multiple"]
            and exact(new["cash"]["equity_multiple"]) < exact(before["cash"]["equity_multiple"]),
            "PDF fiscal value did not reach NOI, cash and ranking")

    restored_files = {p.relative_to(complete): p.read_bytes() for p in complete.rglob("*") if p.is_file()}
    restored = work / "restored"
    require(pilot_run(FIXTURES, restored) == result and pilot_audit(restored) == result
            and all((restored / path).read_bytes() == raw for path, raw in restored_files.items()),
            "Restored PDF sources did not reproduce the whole package")
    scenarios = {}
    for scenario, view in result["deals"][DEAL]["scenarios"].items():
        cash = view["cash"]
        scenarios[scenario] = dict(dated_cash=cash["events"], additional=round(float(exact(cash["total_contributions"]) - 10), 2),
                                   received=round(float(exact(cash["total_distributions"])), 2),
                                   unrecovered=round(float(exact(cash["unrecovered_after_sale"])), 2))
    return dict(status="passed", decision="PENDING", real_decisions_enabled=False, deployment_enabled=False,
                ranking=result["ranking"], scenarios=scenarios, pdf_pages_verified=len(ROLES) * 4,
                blocked_variants=probes, restored_files=len(restored_files),
                tax_change=dict(annual_seller_tax_delta_usd=265, ranking_recomputed=True), pdf_sha256=result["pdf_sha256"])


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d206-") as temp:
        work = args.output or Path(temp)
        work.mkdir(exist_ok=True)
        print(json.dumps(verify(work), ensure_ascii=False, sort_keys=True))
