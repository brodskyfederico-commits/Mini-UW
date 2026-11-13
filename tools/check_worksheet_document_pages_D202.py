"""Exercise page completeness after synthetic PDFs pass file registration."""
from argparse import ArgumentParser
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfWriter

from check_reference_package import require
from check_worksheet_definition_screening_D193 import approvals_unchanged
from check_worksheet_evidence_progressive_order_D164 import variant_pdf
from check_worksheet_technical_acceptance_D200 import cash_summary, settings_for_acceptance, source_files
from miniuw_foundation.scheduled_expense_case import sha
from miniuw_worksheet_v1 import CURRENT_REVISION_FILE, read_package, verify_package
from worksheet_intake_D198 import assemble, register


def verify(output):
    output.mkdir(exist_ok=True)
    sources = source_files(output / "sources")
    settings = settings_for_acceptance()
    expected = assemble(settings, register(sources, "SYNTHETIC-D202-complete"), sources, output / "complete")
    require(expected["simulation_result"] == "PASS", "Complete financial source is unavailable")
    baseline = json.loads((output / "complete/results.json").read_bytes())

    inventory = baseline["local_review"]["bots"]["B03"]["documents"]["plan_pdf"]["sheet_inventory"]
    page, = (row["page"] for row in inventory if "A601" in row["observations"].get("text", {}).get("sheet_claims", []))
    writer = PdfWriter(clone_from=BytesIO(sources["plan_raw"]))
    writer.remove_page(page - 1)
    buffer = BytesIO()
    writer.write(buffer)

    variants = [
        ("missing-a601", "plan_raw", buffer.getvalue(), "Plan.pdf:A601:required_sheet_missing", ()),
        ("missing-downside-bank", "evidence_raw", variant_pdf(sources["evidence_raw"], "downside", drop=True),
         "Evidence.pdf:bank_Downside:evidence_page_role_missing", ("Base",)),
        ("missing-official", "evidence_raw", variant_pdf(sources["evidence_raw"], "official", drop=True),
         "Evidence.pdf:official_snapshot:evidence_page_role_missing", ("Base", "Downside")),
    ]
    results = {}
    for label, argument, raw, blocker, available in variants:
        changed = sources | {argument: raw}
        config = deepcopy(settings)
        if argument == "evidence_raw":
            # Bind the synthetic debt-yield supplement to the new bundle so it
            # cannot conceal the isolated effect of the missing page.
            for term in config["rent_inputs"]["bank_debt_yield"].values():
                term["quote_source_sha256"] = sha(raw)
        folder = output / label
        status = assemble(config, register(changed, f"SYNTHETIC-D202-{label}"), changed, folder)
        require(status["source_blockers"] == [], f"{label}: did not pass file registration")
        saved = read_package(folder)
        model = json.loads(saved["results.json"])
        approvals_unchanged(model)
        audit = verify_package(folder, current_revision_raw=saved[CURRENT_REVISION_FILE])
        require(audit["audit_bot"] == "B16" and audit["vigencia"] == "PENDING"
                and audit["revision_blockers"] == [blocker] and audit["simulation_result"] == "PENDING",
                f"{label}: missing role was not reflected in the audit: {audit}")
        cash = {name: view["cash_per_usd_10"] for name, view in model["scenarios"].items()}
        require(tuple(name for name, value in cash.items() if value is not None) == available,
                f"{label}: cash lost or released for the wrong scenario")
        for name in available:
            verified, prior = cash[name], baseline["scenarios"][name]["cash_per_usd_10"]
            def comparable(story):
                return story | {"events": [{key: value for key, value in row.items() if key != "source_ref"}
                                           for row in story["events"]]}
            require(comparable(verified) == comparable(prior), f"{label}: unaffected cash changed")
        results[label] = dict(blocker=blocker, vigencia=audit["vigencia"], simulation_result=audit["simulation_result"],
                              cash_per_usd_10={name: cash_summary(story) for name, story in cash.items()})
    return dict(status="passed", variants=results, decision="PENDING", deployment_enabled=False,
                real_decisions_enabled=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="miniuw-d202-") as temporary:
        print(json.dumps(verify(args.output or Path(temporary)), ensure_ascii=False, sort_keys=True))
