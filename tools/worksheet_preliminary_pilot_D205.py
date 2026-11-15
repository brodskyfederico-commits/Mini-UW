"""Run or audit the synthetic PRELIMINAR pilot from registered source files."""
from argparse import ArgumentParser
from datetime import date
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from check_reference_package import PackageError, require
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.expense_cash_detail import _json
from miniuw_foundation.inputsheet import inspect_synthetic_input_sheet
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import PRELIMINARY_FLORIDA_TAX_SCHEMA, build_results, encoded
from worksheet_florida_tax_D203 import POLICY as TAX_POLICY
from worksheet_local_sources_D127 import day, object_or_empty, synthetic_id
from worksheet_preliminary_D185 import POLICY, SCENARIOS, SUPPORT, assumption_ready, finish_preliminary
from worksheet_preliminary_pdf_D206 import BANK_ROLES, FILENAME, SCHEMA as PDF_SCHEMA, merge_financing, read_bundle


SCHEMA = "miniuw.synthetic-preliminary-pilot.v1"
PROFILE = "synthetic_preliminary_pilot"
INDEX = "pilot.json"
AREAS = (*SUPPORT, "florida_property_tax")
CELLS = dict(
    program=("C7",),
    acquisition_and_costs=("C32", "C33", "C34", "C35", "C37", "C38", "C39", "C40", "C42"),
    rent_and_expenses=("C8", "C9", "C10", "C11", "C13", "C14", "C15", "C57", "C58", "C59", "C60", "C75", "C76"),
    calendar=("C46", "C47"),
    financing=("C51", "C52", "C53", "C66", "C69", "C70", "C71", "C72", "C73", "C74"),
    exit=("C67", "C68"),
    florida_property_tax=(),
)
MAX_SOURCE_BYTES = 512 * 1024


def paths(deal, scenario, *, pdf=False):
    folder = f"{deal}/{scenario}"
    if pdf:
        return {"Inputs": f"{folder}/Inputs.xlsx", "Evidence": f"{folder}/{FILENAME}"}
    return {"Inputs": f"{folder}/Inputs.xlsx"} | {area: f"{folder}/{area}.json" for area in AREAS}


def read_file(root, name, *, limit=MAX_SOURCE_BYTES):
    path = root / name
    require(not root.is_symlink() and all(not item.is_symlink() for item in (path, *path.parents)
                                         if item != root.parent), f"Enlace simbólico no admitido: {name}")
    if not path.exists():
        return None
    require(path.is_file() and path.stat().st_size <= limit, f"Archivo fuera del perfil: {name}")
    return path.read_bytes()


def read_pilot(directory):
    raw = read_file(directory, INDEX)
    require(raw is not None, f"Falta {INDEX}")
    index = _json(raw, MAX_SOURCE_BYTES)
    require(isinstance(index, dict) and set(index) == {"schema", "as_of", "dates", "focus", "deals", "sha256"}
            and index["schema"] in (SCHEMA, PDF_SCHEMA), "Inventario de piloto sintético inválido")
    deals = index["deals"]
    require(isinstance(deals, list) and 1 <= len(deals) <= 4 and all(
        isinstance(deal, str) and re.fullmatch(r"SYNTHETIC-[A-Z0-9-]{1,22}", deal) for deal in deals
    ) and len(set(deals)) == len(deals) and index["focus"] in deals, "Inventario de deals inválido")
    dates = index["dates"]
    cutoff = day(index["as_of"])
    require(cutoff and isinstance(dates, list) and 3 <= len(dates) <= 9 and all(
        day(value) is not None and day(value) >= cutoff for value in dates), "Calendario del piloto inválido")
    start = date.fromisoformat(dates[0])
    require(all((date.fromisoformat(value).day == start.day
                 and (date.fromisoformat(value).year - start.year) * 12 + date.fromisoformat(value).month - start.month == i * 3)
                for i, value in enumerate(dates)), "El ranking exige el mismo calendario trimestral")
    hashes = index["sha256"]
    names = {name for deal in deals for scenario in SCENARIOS for name in paths(deal, scenario, pdf=index["schema"] == PDF_SCHEMA).values()}
    require(isinstance(hashes, dict) and set(hashes) == names
            and all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes.values()),
            "Se requiere una huella por cada planilla y respaldo")
    sources = {name: data for name in sorted(names) if (data := read_file(directory, name)) is not None}
    return raw, index, sources


def review_scenario(index, sources, deal, scenario):
    records, findings, blockers = {}, {}, []
    pdf = index["schema"] == PDF_SCHEMA
    filenames = paths(deal, scenario, pdf=pdf)
    for role, name in filenames.items():
        raw = sources.get(name)
        observed = sha(raw) if raw is not None else None
        expected = index["sha256"][name]
        error = "archivo ausente" if raw is None else "huella distinta" if observed != expected else None
        findings[role] = dict(path=name, expected_sha256=expected, observed_sha256=observed, blocker=error)
        if error:
            blockers.append(f"{name} · {error}")
    if blockers:
        return records, findings, blockers
    try:
        sheet = inspect_synthetic_input_sheet(sources[filenames["Inputs"]]).cells
    except ValidationError:
        return records, findings, [f"{filenames['Inputs']} · plantilla incompatible"]
    if pdf:
        bundle = filenames["Evidence"]
        pages, issues = read_bundle(sources[bundle], deal, scenario)
        findings["Evidence"]["pages"] = {role: {key: page[key] for key in ("page", "locators")}
                                          for role, page in pages.items()}
        if issues:
            return records, findings, [f"{FILENAME} · {error}" for error in issues]
        summary = pages["A601"]
        if summary["data"] != {"units": pages["A101"]["data"].get("units")} or summary["cells"]:
            return records, findings, [f"{FILENAME} · A101 y A601 difieren en unidades"]
        try:
            finance = merge_financing(pages)
        except ValueError as error:
            return records, findings, [f"{FILENAME} · {error}"]
        plan = pages["A101"]
        documents = {area: pages[area] for area in AREAS if area not in ("program", "financing")}
        documents.update(program=plan, financing=finance)
    for area in AREAS:
        if pdf:
            document = documents[area] | dict(kind=area, deal=deal, scenario=scenario)
            role = "A101" if area == "program" else area
            name = f"{FILENAME} · {role}"
        else:
            name = filenames[area]
            try:
                document = object_or_empty(_json(sources[name], MAX_SOURCE_BYTES))
            except ValidationError:
                document = {}
        data = object_or_empty(document.get("data"))
        claims = object_or_empty(document.get("cells"))
        if ((not pdf and set(document) != {"kind", "deal", "scenario", "data", "cells"}) or document.get("kind") != area
                or document["deal"] != deal or document["scenario"] != scenario
                or not assumption_ready(data, day(index["as_of"])) or not synthetic_id(data["source_ref"])
                or set(claims) != set(CELLS[area])
                or (area == "florida_property_tax" and data.get("policy") != TAX_POLICY)):
            blockers.append(f"{name} · respaldo, identidad o fecha incompatible")
            continue
        for cell, expected in claims.items():
            literal = sheet[cell]["literal"]
            if (not isinstance(expected, str) or literal != expected
                    or sheet[cell]["kind"] not in ("text", "numeric_lexeme")):
                if pdf:
                    page_role = next((bank for bank in BANK_ROLES if cell in pages[bank]["cells"]), role) if area == "financing" else role
                    page = pages[page_role]
                    blockers.append(f"{FILENAME} p. {page['page']} · {page_role} · {cell} difiere de Inputs.xlsx")
                else:
                    blockers.append(f"{name} · {cell} difiere de Inputs.xlsx")
        records[area] = data
    return records, findings, blockers


def calculate(raw_index, index, sources):
    views = {}
    for deal in index["deals"]:
        case = dict(schema=PRELIMINARY_FLORIDA_TAX_SCHEMA, policy=POLICY, focus=deal,
                    as_of=index["as_of"], dates=index["dates"], financing="with_refinance", scenarios={},
                    florida_property_tax=dict(policy=TAX_POLICY, scenarios={}))
        books, findings, blocked = {}, {}, {}
        for scenario in SCENARIOS:
            documents, findings[scenario], blockers = review_scenario(index, sources, deal, scenario)
            if blockers:
                blocked[scenario] = dict(cash=None, blockers=blockers)
                books[scenario] = None
                continue
            path = paths(deal, scenario, pdf=index["schema"] == PDF_SCHEMA)["Inputs"]
            books[scenario] = sources[path]
            if index["schema"] == PDF_SCHEMA:
                evidence = findings[scenario]["Evidence"]
                for area, document in documents.items():
                    role = "A101" if area == "program" else area
                    page_numbers = ("/".join(str(evidence["pages"][bank]["page"]) for bank in BANK_ROLES)
                                    if area == "financing" else evidence["pages"][role]["page"])
                    document["source_ref"] = f"SYNTHETIC-D206-{FILENAME}-p{page_numbers}-{role}"
            fiscal = documents.pop("florida_property_tax")
            fiscal.pop("policy")
            case["florida_property_tax"]["scenarios"][scenario] = fiscal
            case["scenarios"][scenario] = dict(workbook_sha256=index["sha256"][path], support=documents)
        result, _ = build_results(encoded(case), workbook_raw=books["Base"], downside_workbook_raw=books["Downside"])
        computed = result["deals"][deal]["scenarios"]
        views[deal] = dict(scenarios={name: (blocked[name] if name in blocked else computed[name]) |
                                     {"evidence": findings[name]} for name in SCENARIOS})
    return finish_preliminary(index, raw_index, views, profile=PROFILE)


def replay(directory):
    raw, index, sources = read_pilot(directory)
    result, pdf = calculate(raw, index, sources)
    files = {f"sources/{name}": content for name, content in (sources | {INDEX: raw}).items()}
    return files | {"results.json": encoded(result), "MiniUW_Resumen.pdf": pdf}, result


def pilot_run(source, output):
    files, result = replay(source)
    require(not output.is_symlink() and not output.exists() and output.parent.is_dir(),
            "Usá un directorio nuevo con un padre existente")
    with TemporaryDirectory(prefix=".miniuw-pilot-", dir=output.parent) as temp:
        staged = Path(temp) / "pilot"
        for name, data in files.items():
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        staged.rename(output)
    return result


def pilot_audit(output):
    expected, result = replay(output / "sources")
    actual = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file() or path.is_symlink()}
    require(actual == set(expected) and all(read_file(output, name, limit=max(MAX_SOURCE_BYTES, len(data))) == data for name, data in expected.items()),
            "El piloto difiere de la repetición desde los respaldos")
    return result


def pilot_current(output, current_source):
    """Check a replayed package against the independently designated pilot inventory."""
    archived = pilot_audit(output)
    current_sha = None
    blockers = []
    try:
        require(not current_source.resolve().is_relative_to(output.resolve()),
                "La revisión vigente debe designarse fuera del paquete archivado")
        raw, index, sources = read_pilot(current_source)
        current_sha = sha(raw)
        if current_sha != archived["case_sha256"]:
            blockers.append("El inventario vigente difiere de la revisión archivada")
        for name, expected in sorted(index["sha256"].items()):
            if name not in sources:
                blockers.append(f"{name} · falta en la revisión vigente")
            elif sha(sources[name]) != expected:
                blockers.append(f"{name} · huella distinta en la revisión vigente")
        if read_file(current_source, INDEX) != raw:
            blockers.append("El inventario vigente cambió durante el cotejo")
    except (PackageError, ValidationError, ValueError, OSError) as error:
        blockers.append(f"No se pudo cotejar la revisión vigente · {error}")

    return dict(
        vigencia="PENDING" if blockers else "VIGENTE",
        state="PENDING" if blockers else archived["state"],
        decision=archived["decision"],
        ranking=[] if blockers else archived["ranking"],
        pdf_sha256=None if blockers else archived["pdf_sha256"],
        archived_case_sha256=archived["case_sha256"],
        current_case_sha256=current_sha,
        blockers=blockers,
    )


def main():
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("source", type=Path)
    run.add_argument("output", type=Path)
    audit = commands.add_parser("audit")
    audit.add_argument("output", type=Path)
    audit.add_argument("--current-source", type=Path, help="Directorio de la revisión vigente designada")
    documentary = commands.add_parser("intake", help="Cotejar un set real de arquitectura sin calcular caja")
    documentary.add_argument("architecture", type=Path)
    documentary.add_argument("--narrative", type=Path)
    documentary.add_argument("--area-schedule", type=Path)
    documentary.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "intake":
            from worksheet_documentary_intake import intake

            result = intake(args.architecture, narrative=args.narrative, area_schedule=args.area_schedule)
            with args.output.open("xb") as stream:
                stream.write(encoded(result))
            print(json.dumps({key: result[key] for key in ("state", "decision", "ranking")}, ensure_ascii=False))
            return
        if args.command == "audit" and args.current_source is not None:
            print(json.dumps(pilot_current(args.output, args.current_source), ensure_ascii=False))
            return
        result = pilot_run(args.source, args.output) if args.command == "run" else pilot_audit(args.output)
    except (PackageError, ValidationError, ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps({key: result[key] for key in ("state", "decision", "ranking", "pdf_sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
