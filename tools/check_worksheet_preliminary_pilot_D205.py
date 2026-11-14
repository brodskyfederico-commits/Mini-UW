"""Verify ranking, dated investor cash and replay from the D205 source inventory."""
from fractions import Fraction as Q
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from pypdf import PdfReader

from check_reference_package import PackageError, require
from check_worksheet_preliminary_stages_D188 import BOOKS, DEAL, workbook
from check_worksheet_preliminary_tax_D204 import FIXTURE, normalized, verify_portfolio
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import build_results, encoded
from reconcile_worksheet_D179 import exact
from worksheet_preliminary_pilot_D205 import AREAS, CELLS, INDEX, SCENARIOS, SCHEMA, paths, pilot_audit, pilot_run


PILOT_ROOT = FIXTURE.parents[1] / "templates/preliminary-pilot-D205"
SECOND = "SYNTHETIC-LOI-D205-B"


def fixture():
    case = json.loads(FIXTURE.read_bytes())
    files = {}
    for deal in (DEAL, SECOND):
        for scenario in SCENARIOS:
            names = paths(deal, scenario)
            if deal == DEAL:
                book = BOOKS[scenario].read_bytes()
            else:
                edits = {"B3": {"text": deal}}
                if scenario == "Downside":
                    edits["C67"] = {"value": "0.18"}
                book = workbook(scenario, edits)
            files[names["Inputs"]] = book
            sheet = inspect_synthetic_input_sheet(book).cells
            support = case["scenarios"][scenario]["support"]
            fiscal = case["florida_property_tax"]["scenarios"][scenario] | {"policy": case["florida_property_tax"]["policy"]}
            for area in AREAS:
                data = fiscal if area == "florida_property_tax" else support[area]
                files[names[area]] = encoded(dict(kind=area, deal=deal, scenario=scenario, data=data,
                                                 cells={cell: sheet[cell]["literal"] for cell in CELLS[area]}))
    files[INDEX] = encoded(dict(schema=SCHEMA, focus=DEAL, deals=[DEAL, SECOND], as_of=case["as_of"],
                                dates=case["dates"], sha256={name: sha(data) for name, data in files.items()}))
    return files


def document(path, edit, *, register=False):
    body = json.loads(path.read_bytes())
    edit(body)
    raw = encoded(body)
    path.write_bytes(raw)
    if register:
        inventory = path.parents[2] / INDEX
        index = json.loads(inventory.read_bytes())
        index["sha256"][path.relative_to(inventory.parent).as_posix()] = sha(raw)
        inventory.write_bytes(encoded(index))


def verify(work):
    require(fixture() == {path.relative_to(PILOT_ROOT).as_posix(): path.read_bytes()
                         for path in PILOT_ROOT.rglob("*") if path.is_file()}, "Registered fixture drift")
    source = work / "inputs"
    shutil.copytree(PILOT_ROOT, source)
    complete = work / "complete"
    baseline = pilot_run(source, complete)
    require(pilot_audit(complete) == baseline, "Complete pilot did not replay")
    page, = PdfReader(complete / "MiniUW_Resumen.pdf").pages
    require(all(item in page.extract_text() for item in ("Dictamen formal PENDING", DEAL, SECOND, "29,14", "9,06")),
            "One-page report lacks formal gate, ranking or cash")

    candidate = baseline["deals"][DEAL]["scenarios"]
    second = baseline["deals"][SECOND]["scenarios"]
    prior_case = FIXTURE.read_bytes()
    prior, _ = build_results(prior_case, workbook_raw=BOOKS["Base"].read_bytes(), downside_workbook_raw=BOOKS["Downside"].read_bytes())
    require(all(normalized(candidate[name]) == normalized(prior["deals"][DEAL]["scenarios"][name]) for name in SCENARIOS),
            "Assembling from registered files changed prior cash")
    checks = verify_portfolio(prior, json.loads(prior_case))
    downside_noi = exact(candidate["Downside"]["projection"]["sale_noi"])
    expected_delta = downside_noi * (1 / Q("0.16") - 1 / Q("0.18")) * Q("0.94") / 10500
    original_receipts = exact(candidate["Downside"]["cash"]["total_distributions"])
    second_receipts = exact(second["Downside"]["cash"]["total_distributions"])
    require(original_receipts - second_receipts == expected_delta, "Comparator did not reflect the higher exit cap")
    require(baseline["state"] == "PRELIMINAR" and baseline["decision"] == "PENDING"
            and not baseline["deployment_enabled"] and not baseline["real_decisions_enabled"]
            and [(row["deal_id"], row["position"], row["downside_equity_multiple"]) for row in baseline["ranking"]] ==
            [(deal, position, pair["Downside"]["cash"]["equity_multiple"])
             for deal, position, pair in ((DEAL, 1, candidate), (SECOND, 2, second))], "Ranking or guard differs")

    fiscal = paths(DEAL, "Downside")["florida_property_tax"]
    loan = paths(DEAL, "Downside")["financing"]
    rent = paths(DEAL, "Downside")["rent_and_expenses"]
    variants = (
        ("falta-fiscal", fiscal, lambda p: p.unlink(), "archivo ausente"),
        ("falta-financiacion", loan, lambda p: p.unlink(), "archivo ausente"),
        ("respaldo-cambiado", loan, lambda p: document(p, lambda x: x["data"].update(owner="SYNTHETIC-changed")), "huella distinta"),
        ("renta-no-cuadra", rent, lambda p: document(p, lambda x: x["cells"].update(C8="999"), register=True), "C8 difiere"),
        ("fiscal-incompleto", fiscal, lambda p: document(
            p, lambda x: x["data"]["rolls"]["millage"]["2028"].pop("non_school_mills"), register=True), "non_school_mills"),
    )
    probes = {}
    for name, filename, change, expected in variants:
        changed = work / f"sources-{name}"
        shutil.copytree(source, changed)
        change(changed / filename)
        result = pilot_run(changed, work / name)
        view = result["deals"][DEAL]["scenarios"]
        require(result["state"] == result["decision"] == "PENDING" and view["Downside"]["cash"] is None
                and any(expected in issue for issue in view["Downside"]["blockers"])
                and view["Base"] == candidate["Base"]
                and [(row["deal_id"], row["position"]) for row in result["ranking"]] == [(SECOND, 1)],
                f"{name}: affected project was ranked or independent results changed")
        require(pilot_audit(work / name) == result, f"{name}: blocked pilot did not replay")
        probes[name] = view["Downside"]["blockers"]
        if name == "falta-fiscal":
            (changed / filename).write_bytes((source / filename).read_bytes())
            restored = work / "restored"
            require(pilot_run(changed, restored) == baseline and pilot_audit(restored) == baseline, "Restoration changed the result")
            require(all((restored / path.relative_to(complete)).read_bytes() == path.read_bytes()
                        for path in complete.rglob("*") if path.is_file()), "Restoration changed package bytes")

    # Audit detects a source replaced after the package was written.
    shipped = complete / "sources" / loan
    original = shipped.read_bytes()
    try:
        shipped.write_bytes(original + b" ")
        try:
            pilot_audit(complete)
        except PackageError:
            pass
        else:
            require(False, "Audit accepted modified backup")
    finally:
        shipped.write_bytes(original)
    return dict(status="passed", decision="PENDING", deployment_enabled=False, real_decisions_enabled=False,
                ranking=baseline["ranking"], scenarios=checks, missing_or_conflicting_evidence=probes,
                source_files_verified=len(fixture()) - 1, pdf_sha256=baseline["pdf_sha256"])


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d205-") as temp:
        work = args.output or Path(temp)
        work.mkdir(exist_ok=True)
        print(json.dumps(verify(work), ensure_ascii=False, sort_keys=True))
