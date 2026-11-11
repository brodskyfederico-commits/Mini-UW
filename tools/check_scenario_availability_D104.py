"""Audit per-scenario withholding of USD 10 cash when refinance capacity blocks a case."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, require
from check_participant_refinance_variants_D31 import CAPACITY_BLOCKER
from check_unified_worksheet_D48 import call
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import encoded


REPORT = "docs/review/MiniUW_D104_Escenario_Bloqueado_USD10.pdf"
FIXTURE = ROOT / "templates/synthetic-investor-scenarios-D104.json"
LEGACY = ROOT / "templates/synthetic-investor-scenarios-D75.json"
ABOVE_LIMIT = "SYNTHETIC-D31-above-limit"


def run_case(raw, root, name):
    source = root / (name + ".json")
    source.write_bytes(raw)
    package = root / name
    written = call("run", source, "--output", package)
    audited = call("audit", package)
    pdf_path = package / "MiniUW_Resumen.pdf"
    pdf = pdf_path.read_bytes()
    result = json.loads((package / "results.json").read_bytes())
    page, = PdfReader(pdf_path).pages
    require(written["status"] == "written_synthetic_package"
            and audited["status"] == "verified_source_first"
            and result["decision"] == "PENDING"
            and result["personal_investor_return"] is None
            and result["real_decisions_enabled"] is result["deployment_enabled"] is False
            and written["pdf_sha256"] == audited["pdf_sha256"] == result["pdf_sha256"] == sha(pdf),
            f"{name} did not audit or lost the decision guard")
    return result, pdf, page.extract_text()


def build_report():
    source = json.loads(FIXTURE.read_bytes())
    legacy_raw = LEGACY.read_bytes()
    legacy = json.loads(legacy_raw)
    normal = legacy["scenarios"]
    blocked = {"Base": f"{ABOVE_LIMIT}/SYNTHETIC-sale-400", "Downside": f"{ABOVE_LIMIT}/SYNTHETIC-sale-200"}
    require(source["scenarios"] == normal | {"Downside": blocked["Downside"]},
            "The published example must demonstrate a blocked Downside")
    with TemporaryDirectory(prefix="miniuw-d104-") as directory:
        temp = Path(directory)
        prior, _, _ = run_case(legacy_raw, temp, "legacy")
        results = {}
        for label, pending in (("both-available", ()), ("downside-blocked", ("Downside",)),
                               ("base-blocked", ("Base",)), ("both-blocked", ("Base", "Downside"))):
            selection = normal | {name: blocked[name] for name in pending}
            raw = FIXTURE.read_bytes() if label == "downside-blocked" else encoded(source | {"scenarios": selection})
            result, pdf, text = run_case(raw, temp, label)
            require(result["state"] == ("PENDING" if pending else prior["state"]),
                    f"{label} has an incorrect comparison state")
            for name, view in result["scenarios"].items():
                require(view["archive_case"] == selection[name], f"{label} changed its selected source")
                if name in pending:
                    require(view["state"] == "PENDING" and view["blockers"] == [CAPACITY_BLOCKER]
                            and all(view[key] is None for key in ("cash", "ledger_sha256", "gross_sale_proceeds", "sale_closing_costs"))
                            and f"{name} | Retorno por USD 10 PENDING" in text
                            and f"{name} | Por USD 10 iniciales cobrás" not in text,
                            f"{label} exposed money for {name}")
                else:
                    require(view == prior["scenarios"][name] and f"{name} | Por USD 10 iniciales cobrás" in text,
                            f"{label} altered verified cash for {name}")
            require(text.count("El préstamo solicitado supera la capacidad de refinanciación del escenario.") == len(pending)
                    and ("La comparación queda PENDING" in text) == bool(pending),
                    f"{label} does not explain its verified blockers")
            results[label] = dict(state=result["state"], pending=list(pending), pdf_sha256=sha(pdf))
            if label == "downside-blocked":
                example_pdf = pdf

        invalid = (
            ("unknown", source | {"scenarios": normal | {"Downside": "SYNTHETIC-unknown"}}),
            ("unknown-participant", source | {"scenarios": blocked, "participant_id": "SYNTHETIC-unknown"}),
            ("legacy-blocked", legacy | {"scenarios": source["scenarios"]}),
        )
        for name, case in invalid:
            path = temp / (name + ".json")
            path.write_bytes(encoded(case))
            target = temp / name
            call("run", path, "--output", target, blocked=True)
            require(not target.exists(), f"{name} produced a package for a rejected source")

    return example_pdf, dict(status="passed", decision="PENDING", states=results, rejected_cases=len(invalid),
                             one_page_report=True, pdf_sha256=sha(example_pdf))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write the example page instead of auditing its archived copy.")
    args = parser.parse_args()
    pdf, result = build_report()
    if args.output:
        with args.output.open("xb") as output:
            output.write(pdf)
    else:
        require((ROOT / REPORT).read_bytes() == pdf, "The example page differs from the source replay")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
