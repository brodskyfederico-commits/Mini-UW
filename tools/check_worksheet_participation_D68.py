"""Reconcile participant cash and audit the common worksheet package."""
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from pypdf import PdfReader

from check_operating_replay_D20 import ROOT, amount, require
from check_unified_worksheet_D48 import call, save


FIXTURE = "templates/synthetic-unified-worksheet-participation-D68.json"


def verify():
    case = json.loads((ROOT / FIXTURE).read_bytes())
    with TemporaryDirectory(prefix="miniuw-d68-") as temp:
        root = Path(temp)
        for key in ("price_400", "price_500", "explicit_zero", "tax_pending"):
            folder = root / key
            source = folder.with_suffix(".json")
            save(source, case | {"archive_case": key})
            written = call("run", source, "--output", folder)
            checked = call("audit", folder)
            result = json.loads((folder / "results.json").read_bytes())
            page, = PdfReader(folder / "MiniUW_Resumen.pdf").pages
            text = page.extract_text()
            report = result["synthetic_cash_participation"]
            require(written["pdf_sha256"] == checked["pdf_sha256"] == result["pdf_sha256"]
                    and result["decision"] == report["decision"] == "PENDING"
                    and result["personal_investor_return"] is report["personal_investor_return"] is None
                    and report["terms_sha256"] == case["allocation_terms_sha256"]
                    and result["deployment_enabled"] is result["real_decisions_enabled"] is False,
                    "Allocation changed a decision or detached from the terms")
            if key == "tax_pending":
                require(result["project"] is report["participants"] is report["reconciliation"] is None
                        and report["blockers"] == ["current_project_cash_unavailable"]
                        and "Reparto sintetico pendiente." in text,
                        "A blocked sale exposed participant cash")
                continue

            project = result["project"]
            people = report["participants"]
            require(report["state"] == "computed_synthetic_cash_allocation"
                    and [amount(p["share_fraction"]) for p in people] == [Fraction(1, 4), Fraction(3, 4)]
                    and "Reparto hipotetico" in text and report["project_ledger_sha256"],
                    "Archived allocation terms did not reach the page and report")
            fields = ("gross_contributions", "gross_distributions", "net_cash_profit")
            for field in fields:
                require(sum(amount(p[field]) for p in people) == amount(project[field]),
                        f"Participants do not reconcile to the project: {field}")
            for i, event in enumerate(project["events"]):
                require(sum(amount(p["dated_events"][i]["amount"]) for p in people) == amount(event["amount"])
                        and all(p["dated_events"][i]["date"] == event["date"]
                                and p["dated_events"][i]["project_event_pointer"] == f"/project/events/{i}"
                                for p in people),
                        f"Participant cash differs on event {i}")
            for part in people:
                require(part["participant_id"] in text and part["verified_personal_investor_return"] is None,
                        "A participant is missing or mislabeled in the one-page report")
            require(report["risk"]["state"] == "computed_synthetic_cash_risk_observations",
                    "The same cash allocation did not reach funding and sale risk")

        wrong = root / "wrong-terms.json"
        save(wrong, case | {"allocation_terms_sha256": "0" * 64})
        call("run", wrong, "--output", root / "wrong-terms", blocked=True)
    return dict(status="passed", decision="PENDING", audited_pages=4, allocated=3,
                pending=1, mismatched_terms_rejected=True)


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error), "decision": "PENDING"}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
